from asyncio import gather
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Coroutine, Dict, List, Optional, Callable, Tuple, Union, Awaitable
from typing_extensions import Literal

from dff.script import Context

ALL_ITEMS = "__all__"
"""
`__all__` - the default value for all `DictSchemaField`s:
it means that all keys of the dictionary or list will be read or written.
Can be used as a value of `subscript` parameter for `DictSchemaField`s and `ListSchemaField`s.
"""

_ReadPackedContextFunction = Callable[[str], Awaitable[Tuple[Dict, Optional[str]]]]
# TODO!

_ReadLogContextFunction = Callable[[Optional[int], int, str, str], Awaitable[Dict]]
# TODO!

_WritePackedContextFunction = Callable[[Dict, str, str], Awaitable]
# TODO!

_WriteLogContextFunction = Callable[[List[Tuple[str, int, Any]], str], Coroutine]
# TODO!


class SchemaField(BaseModel):
    """
    Schema for context fields that are dictionaries with numeric keys fields.
    Used for controlling read / write policy of the particular field.
    """

    name: str = Field("", allow_mutation=False)
    """
    `name` is the name of backing Context field.
    It can not (and should not) be changed in runtime.
    """

    subscript: Union[Literal["__all__"], int] = 3
    """
    `subscript` is used for limiting keys for reading and writing.
    It can be a string `__all__` meaning all existing keys or number,
    positive for first **N** keys and negative for last **N** keys.
    Keys should be sorted as numbers.
    Default: -3.
    """

    class Config:
        validate_assignment = True


class ExtraFields(str, Enum):
    """
    Enum, conaining special :py:class:`dff.script.Context` field names.
    These fields only can be used for data manipulation within context storage.
    """

    active_ctx = "active_ctx"
    primary_id = "_primary_id"
    storage_key = "_storage_key"
    created_at = "_created_at"
    updated_at = "_updated_at"


class ContextSchema(BaseModel):
    """
    Schema, describing how :py:class:`dff.script.Context` fields should be stored and retrieved from storage.
    Allows fields ignoring, filtering, sorting and partial reading and writing of dictionary fields.
    """

    requests: SchemaField = Field(SchemaField(name="requests"), allow_mutation=False)
    """
    Field for storing Context field `requests`.
    """

    responses: SchemaField = Field(SchemaField(name="responses"), allow_mutation=False)
    """
    Field for storing Context field `responses`.
    """

    labels: SchemaField = Field(SchemaField(name="labels"), allow_mutation=False)
    """
    Field for storing Context field `labels`.
    """

    append_single_log: bool = True

    supports_async: bool = False

    class Config:
        validate_assignment = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def read_context(self, pac_reader: _ReadPackedContextFunction, log_reader: _ReadLogContextFunction, storage_key: str) -> Context:
        """
        Read context from storage.
        Calculate what fields (and what keys of what fields) to read, call reader function and cast result to context.
        `pac_reader` - the function used for context reading from a storage (see :py:const:`~._ReadContextFunction`).
        `storage_key` - the key the context is stored with (used in cases when the key is not preserved in storage).
        `primary_id` - the context unique identifier.
        returns tuple of context and context hashes
        (hashes should be kept and passed to :py:func:`~.ContextSchema.write_context`).
        """
        ctx_dict, primary_id = await pac_reader(storage_key)
        if primary_id is None:
            raise KeyError(f"No entry for key {primary_id}.")

        tasks = dict()
        for field_props in [value for value in dict(self).values() if isinstance(value, SchemaField)]:
            field_name = field_props.name
            nest_dict = ctx_dict[field_name]
            if isinstance(field_props.subscript, int):
                if len(nest_dict) > field_props.subscript:
                    last_keys = sorted(nest_dict.keys())[-field_props.subscript:]
                    ctx_dict[field_name] = {k: v for k, v in nest_dict.items() if k in last_keys}
                elif len(nest_dict) < field_props.subscript:
                    limit = field_props.subscript - len(nest_dict)
                    tasks[field_name] = log_reader(limit, len(nest_dict), field_name, primary_id)
            else:
                tasks[field_name] = log_reader(None, len(nest_dict), field_name, primary_id)

        if self.supports_async:
            tasks = dict(zip(tasks.keys(), await gather(*tasks.values())))
        else:
            tasks = {key: await task for key, task in tasks.items()}

        for field_name in tasks.keys():
            ctx_dict[field_name].update(tasks[field_name])

        ctx = Context.cast(ctx_dict)
        setattr(ctx, ExtraFields.primary_id.value, primary_id)
        setattr(ctx, ExtraFields.storage_key.value, storage_key)
        return ctx

    async def write_context(
        self,
        ctx: Context,
        pac_writer: _WritePackedContextFunction,
        log_writer: _WriteLogContextFunction,
        storage_key: str,
        chunk_size: Union[Literal[False], int] = False,
    ):
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
        ctx_dict = ctx.dict()
        logs_dict = dict()
        primary_id = getattr(ctx, ExtraFields.primary_id.value, str(uuid4()))

        for field_props in [value for value in dict(self).values() if isinstance(value, SchemaField)]:
            nest_dict = ctx_dict[field_props.name]
            last_keys = sorted(nest_dict.keys())

            if self.append_single_log:
                logs_dict[field_props.name] = dict()
                if len(last_keys) > 0:
                    logs_dict[field_props.name] = {last_keys[-1]: nest_dict[last_keys[-1]]}
            else:
                logs_dict[field_props.name] = nest_dict

            if isinstance(field_props.subscript, int):
                last_keys = last_keys[-field_props.subscript:]

            ctx_dict[field_props.name] = {k:v for k, v in nest_dict.items() if k in last_keys}

        await pac_writer(ctx_dict, storage_key, primary_id)

        flattened_dict = list()
        for field, payload in logs_dict.items():
            for key, value in payload.items():
                flattened_dict += [(field, key, value)]
        if len(flattened_dict) > 0:
            if not bool(chunk_size):
                await log_writer(flattened_dict, primary_id)
            else:
                tasks = list()
                for ch in range(0, len(flattened_dict), chunk_size):
                    next_ch = ch + chunk_size
                    chunk = flattened_dict[ch:next_ch]
                    tasks += [log_writer(chunk, primary_id)]
                if self.supports_async:
                    await gather(*tasks)
                else:
                    for task in tasks:
                        await task

        setattr(ctx, ExtraFields.primary_id.value, primary_id)
        setattr(ctx, ExtraFields.storage_key.value, storage_key)
