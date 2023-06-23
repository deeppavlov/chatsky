from asyncio import gather, get_event_loop, create_task
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, Field, PrivateAttr, validator
from typing import Any, Coroutine, Dict, List, Optional, Callable, Tuple, Union, Awaitable
from typing_extensions import Literal

from dff.script import Context

ALL_ITEMS = "__all__"
"""
`__all__` - the default value for all `DictSchemaField`s:
it means that all keys of the dictionary or list will be read or written.
Can be used as a value of `subscript` parameter for `DictSchemaField`s and `ListSchemaField`s.
"""

_ReadPackedContextFunction = Callable[[str, str], Awaitable[Dict]]
# TODO!

_ReadLogContextFunction = Callable[[str, str], Awaitable[Dict]]
# TODO!

_WritePackedContextFunction = Callable[[Dict, str, str], Awaitable]
# TODO!

_WriteLogContextFunction = Callable[[List[Tuple[str, int, Any]], str, str], Coroutine]
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

    _subscript_callback: Callable = PrivateAttr(default=lambda: None)
    # TODO!

    class Config:
        validate_assignment = True

    @validator("subscript")
    def _run_callback_before_changing_subscript(cls, value: Any, values: Dict):
        if "_subscript_callback" in values:
            values["_subscript_callback"]()
        return value


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

    _pending_futures: List[Awaitable] = PrivateAttr(default=list())
    # TODO!

    class Config:
        validate_assignment = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        field_props: SchemaField
        for field_props in dict(self).values():
            field_props.__setattr__("_subscript_callback", self.close)

    def __del__(self):
        self.close()

    def close(self):
        async def _await_all_pending_transactions():
            await gather(*self._pending_futures)

        try:
            loop = get_event_loop()
            if loop.is_running():
                loop.create_task(_await_all_pending_transactions())
            else:
                loop.run_until_complete(_await_all_pending_transactions())
        except Exception:
            pass

    async def read_context(self, pac_reader: _ReadPackedContextFunction, log_reader: _ReadLogContextFunction, storage_key: str, primary_id: str) -> Context:
        """
        Read context from storage.
        Calculate what fields (and what keys of what fields) to read, call reader function and cast result to context.
        `pac_reader` - the function used for context reading from a storage (see :py:const:`~._ReadContextFunction`).
        `storage_key` - the key the context is stored with (used in cases when the key is not preserved in storage).
        `primary_id` - the context unique identifier.
        returns tuple of context and context hashes
        (hashes should be kept and passed to :py:func:`~.ContextSchema.write_context`).
        # TODO: handle case when required subscript is more than received.
        """
        ctx_dict = await pac_reader(storage_key, primary_id)
        ctx_dict[ExtraFields.primary_id.value] = primary_id

        ctx = Context.cast(ctx_dict)
        ctx.__setattr__(ExtraFields.storage_key.value, storage_key)
        return ctx

    async def write_context(
        self,
        ctx: Context,
        pac_writer: _WritePackedContextFunction,
        log_writer: _WriteLogContextFunction,
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
        logs_dict = dict()
        primary_id = str(uuid4()) if primary_id is None else primary_id

        field_props: SchemaField
        for field_props in dict(self).values():
            nest_dict = ctx_dict[field_props.name]
            logs_dict[field_props.name] = nest_dict
            last_keys = sorted(nest_dict.keys())
            if isinstance(field_props.subscript, int):
                last_keys = last_keys[-field_props.subscript:]
            ctx_dict[field_props.name] = {k:v for k, v in nest_dict.items() if k in last_keys}

        await pac_writer(ctx_dict, storage_key, primary_id)

        flattened_dict = list()
        for field, payload in logs_dict.items():
            for key, value in payload.items():
                flattened_dict += [(field, key, value)]
        if not bool(chunk_size):
            self._pending_futures += [create_task(log_writer(flattened_dict, storage_key, primary_id))]
        else:
            for ch in range(0, len(flattened_dict), chunk_size):
                next_ch = ch + chunk_size
                chunk = flattened_dict[ch:next_ch]
                self._pending_futures += [create_task(log_writer(chunk, storage_key, primary_id))]
        return primary_id
