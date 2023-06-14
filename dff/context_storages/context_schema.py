import time
from hashlib import sha256
from enum import Enum
import uuid
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple, Callable, Any, Union, Awaitable, Hashable
from typing_extensions import Literal

from dff.script import Context

ALL_ITEMS = "__all__"
"""
`__all__` - the default value for all `DictSchemaField`s:
it means that all keys of the dictionary or list will be read or written.
Can be used as a value of `subscript` parameter for `DictSchemaField`s and `ListSchemaField`s.
"""


class SchemaFieldReadPolicy(str, Enum):
    """
    Read policy of context field.
    The following policies are supported:

    - READ: the context field is read from the context storage (default),
    - IGNORE: the context field is completely ignored in runtime
        (it can be still used with other tools for accessing database, like statistics).
    """

    READ = "read"
    IGNORE = "ignore"


class SchemaFieldWritePolicy(str, Enum):
    """
    Write policy of context field.
    The following policies are supported:

    - IGNORE: the context field is completely ignored in runtime,
    - UPDATE: the context field is unconditionally updated every time (default for `ValueSchemaField`s),
    - HASH_UPDATE: the context field is updated only if it differs from the value in storage
        (sha256 will be used to calculate difference, for dictionary the difference is calculated key-wise),
    - APPEND: the context field will be updated only if it doesn't exist in storage
        (for dictionary only the missing keys will be added).
    """

    IGNORE = "ignore"
    UPDATE = "update"
    HASH_UPDATE = "hash_update"
    APPEND = "append"


FieldDescriptor = Union[Dict[str, Tuple[Any, bool]], Tuple[Any, bool]]
"""
Field descriptor type.
It contains data and boolean (if writing of data should be enforced).
Field can be dictionary or single value.
In case if the field is a dictionary:
field descriptior is the dictionary; to each value the enforced boolean is added (each value is a tuple).
In case if the field is a value:
field descriptior is the tuple of the value and enforced boolean.
"""

_ReadContextFunction = Callable[[Dict[str, Union[bool, int, List[Hashable]]], str], Awaitable[Dict]]
"""
Context reader function type.
The function accepts subscript, that is a dict, where keys context field names to read.
The dict values are:
- booleans: that means that the whole field should be read (`True`) or ignored (`False`),
- ints: that means that if the field is a dict, only **N** first keys should be read
    if **N** is positive, else last **N** keys. Keys should be sorted as numbers if they are numeric
    or lexicographically if at least some of them are strings,
- list: that means that only keys that belong to the list should be read, others should be ignored.
The function is asynchronous, it returns dictionary representation of Context.
"""

_WriteContextFunction = Callable[[Optional[str], FieldDescriptor, bool, str], Awaitable]
"""
Context writer function type.
The function will be called multiple times: once for each dictionary field of Context.
It will be called once more for the whole context itself for writing its' value fields.
The function accepts:
- field name: string, the name of field to write, None if writing the whole context,
- field descriptor: dictionary, representing data to be written and if writing of the data should be enforced,
- nested flag: boolean, `True` if writing dictionary field of Context, `False` if writing the Context itself,
- primary id: string primary identificator of the context.
The function is asynchronous, it returns None.
"""


class BaseSchemaField(BaseModel):
    """
    Base class for context field schema.
    Used for controlling read / write policy of the particular field.
    """

    name: str = Field("", allow_mutation=False)
    """
    `name` is the name of backing Context field.
    It can not (and should not) be changed in runtime.
    """
    on_read: SchemaFieldReadPolicy = SchemaFieldReadPolicy.READ
    """
    `on_read` is the default field read policy.
    Default: :py:const:`~.SchemaFieldReadPolicy.READ`.
    """
    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.IGNORE
    """
    `on_write` is the default field write policy.
    Default: :py:const:`~.SchemaFieldReadPolicy.IGNORE`.
    """

    class Config:
        validate_assignment = True


class ListSchemaField(BaseSchemaField):
    """
    Schema for context fields that are dictionaries with numeric keys fields.
    """

    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.APPEND
    """
    Default: :py:const:`~.SchemaFieldReadPolicy.APPEND`.
    """
    subscript: Union[Literal["__all__"], int] = -3
    """
    `subscript` is used for limiting keys for reading and writing.
    It can be a string `__all__` meaning all existing keys or number,
    positive for first **N** keys and negative for last **N** keys.
    Keys should be sorted as numbers.
    Default: -3.
    """


class DictSchemaField(BaseSchemaField):
    """
    Schema for context fields that are dictionaries with string keys fields.
    """

    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.HASH_UPDATE
    """
    Default: :py:const:`~.SchemaFieldReadPolicy.HASH_UPDATE`.
    """
    subscript: Union[Literal["__all__"], List[Hashable]] = ALL_ITEMS
    """
    `subscript` is used for limiting keys for reading and writing.
    It can be a string `__all__` meaning all existing keys or number,
    positive for first **N** keys and negative for last **N** keys.
    Keys should be sorted as lexicographically.
    Default: `__all__`.
    """


class ValueSchemaField(BaseSchemaField):
    """
    Schema for context fields that aren't dictionaries.
    """

    on_write: SchemaFieldWritePolicy = SchemaFieldWritePolicy.UPDATE
    """
    Default: :py:const:`~.SchemaFieldReadPolicy.UPDATE`.
    """


class FrozenValueSchemaField(ValueSchemaField):
    """
    Immutable schema for context fields that aren't dictionaries.
    Schema should be used for keys that are used to keep database integrity
    and whose policies shouldn't be changed by user.
    """

    class Config:
        allow_mutation = False


class ExtraFields(str, Enum):
    """
    Enum, conaining special :py:class:`dff.script.Context` field names.
    These fields only can be used for data manipulation within context storage.
    """

    primary_id = "primary_id"
    storage_key = "_storage_key"
    active_ctx = "active_ctx"
    created_at = "created_at"
    updated_at = "updated_at"


class ContextSchema(BaseModel):
    """
    Schema, describing how :py:class:`dff.script.Context` fields should be stored and retrieved from storage.
    Allows fields ignoring, filtering, sorting and partial reading and writing of dictionary fields.
    """

    active_ctx: ValueSchemaField = Field(FrozenValueSchemaField(name=ExtraFields.active_ctx), allow_mutation=False)
    """
    Special field for marking currently active context.
    Not active contexts are still stored in storage for statistical purposes.
    Properties of this field can't be changed.
    """
    storage_key: ValueSchemaField = Field(FrozenValueSchemaField(name=ExtraFields.storage_key), allow_mutation=False)
    """
    Special field for key under that the context was stored (Context property `storage_key`).
    Properties of this field can't be changed.
    """
    requests: ListSchemaField = ListSchemaField(name="requests")
    """
    Field for storing Context field `requests`.
    """
    responses: ListSchemaField = ListSchemaField(name="responses")
    """
    Field for storing Context field `responses`.
    """
    labels: ListSchemaField = ListSchemaField(name="labels")
    """
    Field for storing Context field `labels`.
    """
    misc: DictSchemaField = DictSchemaField(name="misc")
    """
    Field for storing Context field `misc`.
    """
    framework_states: DictSchemaField = DictSchemaField(name="framework_states")
    """
    Field for storing Context field `framework_states`.
    """
    created_at: ValueSchemaField = ValueSchemaField(name=ExtraFields.created_at, on_write=SchemaFieldWritePolicy.APPEND)
    """
    Special field for keeping track of time the context was first time stored.
    """
    updated_at: ValueSchemaField = ValueSchemaField(name=ExtraFields.updated_at)
    """
    Special field for keeping track of time the context was last time updated.
    """

    class Config:
        validate_assignment = True

    def _calculate_hashes(self, value: Union[Dict[str, Any], Any]) -> Union[Dict[str, Any], Hashable]:
        """
        Calculate hashes for a context field: single hashes for value fields
        and dictionary of hashes for dictionary fields.
        """
        if isinstance(value, dict):
            return {k: sha256(str(v).encode("utf-8")) for k, v in value.items()}
        else:
            return sha256(str(value).encode("utf-8"))

    async def read_context(
        self, ctx_reader: _ReadContextFunction, storage_key: str, primary_id: str
    ) -> Tuple[Context, Dict]:
        """
        Read context from storage.
        Calculate what fields (and what keys of what fields) to read, call reader function and cast result to context.
        `ctx_reader` - the function used for context reading from a storage (see :py:const:`~._ReadContextFunction`).
        `storage_key` - the key the context is stored with (used in cases when the key is not preserved in storage).
        `primary_id` - the context unique identifier.
        returns tuple of context and context hashes
        (hashes should be kept and passed to :py:func:`~.ContextSchema.write_context`).
        """
        fields_subscript = dict()

        field_props: BaseSchemaField
        for field_props in dict(self).values():
            field = field_props.name
            if field_props.on_read == SchemaFieldReadPolicy.IGNORE:
                fields_subscript[field] = False
            elif isinstance(field_props, ListSchemaField) or isinstance(field_props, DictSchemaField):
                fields_subscript[field] = field_props.subscript
            else:
                fields_subscript[field] = True

        hashes = dict()
        ctx_dict = await ctx_reader(fields_subscript, primary_id)
        for key in ctx_dict.keys():
            hashes[key] = self._calculate_hashes(ctx_dict[key])

        ctx = Context.cast(ctx_dict)
        ctx.__setattr__(ExtraFields.storage_key.value, storage_key)
        return ctx, hashes

    async def write_context(
        self,
        ctx: Context,
        hashes: Optional[Dict],
        val_writer: _WriteContextFunction,
        storage_key: str,
        primary_id: Optional[str],
        chunk_size: Union[Literal[False], int] = False,
    ) -> str:
        """
        Write context to storage.
        Calculate what fields (and what keys of what fields) to write,
        split large data into chunks if needed and call writer function.
        `ctx` - the context to write.
        `hashes` - hashes calculated for context during previous reading,
            used only for :py:const:`~.SchemaFieldReadPolicy.UPDATE_HASHES`.
        `val_writer` - the function used for context writing to a storage (see :py:const:`~._WriteContextFunction`).
        `storage_key` - the key the context is stored with.
        `primary_id` - the context unique identifier,
            should be None if this is the first time writing this context,
            otherwise the context will be overwritten.
        `chunk_size` - chunk size for large dictionaries writing,
            should be set to integer in case the storage has any writing query limitations,
            otherwise should be boolean `False` or number `0`.
        returns string, the context primary id.
        """
        ctx.__setattr__(ExtraFields.storage_key.value, storage_key)
        ctx_dict = ctx.dict()
        primary_id = str(uuid.uuid4()) if primary_id is None else primary_id

        ctx_dict[ExtraFields.storage_key.value] = storage_key
        ctx_dict[self.active_ctx.name] = True
        ctx_dict[self.created_at.name] = ctx_dict[self.updated_at.name] = time.time_ns()

        flat_values = dict()
        field_props: BaseSchemaField
        for field_props in dict(self).values():
            field = field_props.name
            update_values = ctx_dict[field]
            update_nested = not isinstance(field_props, ValueSchemaField)
            if field_props.on_write == SchemaFieldWritePolicy.IGNORE:
                continue
            elif field_props.on_write == SchemaFieldWritePolicy.HASH_UPDATE:
                update_enforce = True
                if hashes is not None and hashes.get(field) is not None:
                    new_hashes = self._calculate_hashes(ctx_dict[field])
                    if isinstance(new_hashes, dict):
                        update_values = {k: v for k, v in ctx_dict[field].items() if hashes[field][k] != new_hashes[k]}
                    else:
                        update_values = ctx_dict[field] if hashes[field] != new_hashes else False
            elif field_props.on_write == SchemaFieldWritePolicy.APPEND:
                update_enforce = False
            else:
                update_enforce = True
            if update_nested:
                if not bool(chunk_size):
                    await val_writer(field, (update_values, update_enforce), True, primary_id)
                else:
                    for ch in range(0, len(update_values), chunk_size):
                        next_ch = ch + chunk_size
                        chunk = {k: update_values[k] for k in list(update_values.keys())[ch:next_ch]}
                        await val_writer(field, (chunk, update_enforce), True, primary_id)
            else:
                flat_values.update({field: (update_values, update_enforce)})
        await val_writer(None, flat_values, False, primary_id)
        return primary_id
