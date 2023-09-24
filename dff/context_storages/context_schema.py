"""
Context Schema
--------------
The `ContextSchema` module provides class for managing context storage rules.
The :py:class:`~.Context` will be stored in two instances, `CONTEXT` and `LOGS`,
that can be either files, databases or namespaces. The context itself alongside with
several latest requests, responses and labels are stored in `CONTEXT` table,
while the older ones are kept in `LOGS` table and not accessed too often.
"""

import time
from asyncio import gather
from uuid import uuid4
from enum import Enum
from pydantic import BaseModel, Field, PositiveInt
from typing import Any, Coroutine, List, Dict, Optional, Callable, Tuple, Union, Awaitable
from typing_extensions import Literal

from dff.script import Context

ALL_ITEMS = "__all__"
"""
The default value for `subscript` parameter of :py:class:`~.SchemaField`:
it means that all keys of the dictionary or list will be read or written.
"""

_ReadPackedContextFunction = Callable[[str], Awaitable[Tuple[Dict, Optional[str]]]]
"""
Type alias of asynchronous function that should be called in order to retrieve context
data from `CONTEXT` table. Matches type of :py:func:`DBContextStorage._read_pac_ctx` method.
"""

_ReadLogContextFunction = Callable[[Optional[int], str, str], Awaitable[Dict]]
"""
Type alias of asynchronous function that should be called in order to retrieve context
data from `LOGS` table. Matches type of :py:func:`DBContextStorage._read_log_ctx` method.
"""

_WritePackedContextFunction = Callable[[Dict, int, int, str, str], Awaitable]
"""
Type alias of asynchronous function that should be called in order to write context
data to `CONTEXT` table. Matches type of :py:func:`DBContextStorage._write_pac_ctx` method.
"""

_WriteLogContextFunction = Callable[[List[Tuple[str, int, Any]], int, str], Awaitable]
"""
Type alias of asynchronous function that should be called in order to write context
data to `LOGS` table. Matches type of :py:func:`DBContextStorage._write_log_ctx` method.
"""


class SchemaField(BaseModel, validate_assignment=True):
    """
    Schema for :py:class:`~.Context` fields that are dictionaries with numeric keys fields.
    Used for controlling read and write policy of the particular field.
    """

    name: str = Field(default_factory=str, frozen=True)
    """
    `name` is the name of backing :py:class:`~.Context` field.
    It can not (and should not) be changed in runtime.
    """

    subscript: Union[Literal["__all__"], int] = 3
    """
    `subscript` is used for limiting keys for reading and writing.
    It can be a string `__all__` meaning all existing keys or number,
    negative for first **N** keys and positive for last **N** keys.
    Keys should be sorted as numbers.
    Default: 3.
    """


class ExtraFields(str, Enum):
    """
    Enum, conaining special :py:class:`~.Context` field names.
    These fields only can be used for data manipulation within context storage.
    `active_ctx` is a special field that is populated for internal DB usage only.
    """

    active_ctx = "active_ctx"
    primary_id = "_primary_id"
    storage_key = "_storage_key"
    created_at = "_created_at"
    updated_at = "_updated_at"


class ContextSchema(BaseModel, validate_assignment=True, arbitrary_types_allowed=True):
    """
    Schema, describing how :py:class:`~.Context` fields should be stored and retrieved from storage.
    The default behaviour is the following: All the context data except for the fields that are
    dictionaries with numeric keys is serialized and stored in `CONTEXT` **table** (this instance
    is a table for SQL context storages only, it can also be a file or a namespace for different backends).
    For the dictionaries with numeric keys, their entries are sorted according to the key and the last
    few are included into `CONTEXT` table, while the rest are stored in `LOGS` table.

    That behaviour allows context storage to minimize the operation number for context reading and
    writing.
    """

    requests: SchemaField = Field(default_factory=lambda: SchemaField(name="requests"), frozen=True)
    """
    `SchemaField` for storing Context field `requests`.
    """

    responses: SchemaField = Field(default_factory=lambda: SchemaField(name="responses"), frozen=True)
    """
    `SchemaField` for storing Context field `responses`.
    """

    labels: SchemaField = Field(default_factory=lambda: SchemaField(name="labels"), frozen=True)
    """
    `SchemaField` for storing Context field `labels`.
    """

    append_single_log: bool = True
    """
    If set will *not* write only one value to LOGS table each turn.

    Example:
    If `labels` field contains 7 entries and its subscript equals 3, (that means that 4 labels
    were added during current turn), if `duplicate_context_in_logs` is set to False:

    - If `append_single_log` is True:
       only the first label will be written to `LOGS`.
    - If `append_single_log` is False:
       all 4 first labels will be written to `LOGS`.

    """

    duplicate_context_in_logs: bool = False
    """
    If set will *always* backup all items in `CONTEXT` table in `LOGS` table

    Example:
    If `labels` field contains 7 entries and its subscript equals 3 and `append_single_log`
    is set to False:

    - If `duplicate_context_in_logs` is False:
       the last 3 entries will be stored in `CONTEXT` table and 4 first will be stored in `LOGS`.
    - If `duplicate_context_in_logs` is True:
       the last 3 entries will be stored in `CONTEXT` table and all 7 will be stored in `LOGS`.

    """

    supports_async: bool = False
    """
    If set will try to perform *some* operations asynchronously.

    WARNING! Be careful with this flag. Some databases support asynchronous reads and writes,
    and some do not. For all `DFF` context storages it will be set automatically during `__init__`.
    Change it only if you implement a custom context storage.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def read_context(
        self, pac_reader: _ReadPackedContextFunction, log_reader: _ReadLogContextFunction, storage_key: str
    ) -> Context:
        """
        Read context from storage.
        Calculate what fields to read, call reader function and cast result to context.
        Also set `primary_id` and `storage_key` attributes of the read context.

        :param pac_reader: the function used for reading context from
            `CONTEXT` table (see :py:const:`~._ReadPackedContextFunction`).
        :param log_reader: the function used for reading context from
            `LOGS` table (see :py:const:`~._ReadLogContextFunction`).
        :param storage_key: the key the context is stored with.

        :return: the read :py:class:`~.Context` object.
        """
        ctx_dict, primary_id = await pac_reader(storage_key)
        if primary_id is None:
            raise KeyError(f"No entry for key {primary_id}.")

        tasks = dict()
        for field_props in [value for value in dict(self).values() if isinstance(value, SchemaField)]:
            field_name = field_props.name
            nest_dict: Dict[int, Any] = ctx_dict[field_name]
            if isinstance(field_props.subscript, int):
                sorted_dict = sorted(list(nest_dict.keys()))
                last_read_key = sorted_dict[-1] if len(sorted_dict) > 0 else 0
                # If whole context is stored in `CONTEXTS` table - no further reads needed.
                if len(nest_dict) > field_props.subscript:
                    limit = -field_props.subscript
                    last_keys = sorted(nest_dict.keys())[limit:]
                    ctx_dict[field_name] = {k: v for k, v in nest_dict.items() if k in last_keys}
                # If there is a need to read somethig from `LOGS` table - create reading tasks.
                elif len(nest_dict) < field_props.subscript and last_read_key > field_props.subscript:
                    limit = field_props.subscript - len(nest_dict)
                    tasks[field_name] = log_reader(limit, field_name, primary_id)
            else:
                tasks[field_name] = log_reader(None, field_name, primary_id)

        if self.supports_async:
            tasks = dict(zip(tasks.keys(), await gather(*tasks.values())))
        else:
            tasks = {key: await task for key, task in tasks.items()}

        for field_name, log_dict in tasks.items():
            ctx_dict[field_name].update(log_dict)

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
        chunk_size: Union[Literal[False], PositiveInt] = False,
    ):
        """
        Write context to storage.
        Calculate what fields to write, split large data into chunks if needed and call writer function.
        Also update `updated_at` attribute of the given context with current time, set `primary_id` and `storage_key`.

        :param ctx: the context to store.
        :param pac_writer: the function used for writing context to
            `CONTEXT` table (see :py:const:`~._WritePackedContextFunction`).
        :param log_writer: the function used for writing context to
            `LOGS` table (see :py:const:`~._WriteLogContextFunction`).
        :param storage_key: the key to store the context with.
        :param chunk_size: maximum number of items that can be inserted simultaneously, False if no such limit exists.

        :return: the read :py:class:`~.Context` object.
        """
        updated_at = time.time_ns()
        setattr(ctx, ExtraFields.updated_at.value, updated_at)
        created_at = getattr(ctx, ExtraFields.created_at.value, updated_at)

        ctx_dict = ctx.model_dump()
        logs_dict = dict()
        primary_id = getattr(ctx, ExtraFields.primary_id.value, str(uuid4()))

        for field_props in [value for value in dict(self).values() if isinstance(value, SchemaField)]:
            nest_dict = ctx_dict[field_props.name]
            last_keys = sorted(nest_dict.keys())

            if (
                self.append_single_log
                and isinstance(field_props.subscript, int)
                and len(nest_dict) > field_props.subscript
            ):
                unfit = -field_props.subscript - 1
                logs_dict[field_props.name] = {last_keys[unfit]: nest_dict[last_keys[unfit]]}
            else:
                if self.duplicate_context_in_logs or not isinstance(field_props.subscript, int):
                    logs_dict[field_props.name] = nest_dict
                else:
                    limit = -field_props.subscript
                    logs_dict[field_props.name] = {key: nest_dict[key] for key in last_keys[:limit]}

            if isinstance(field_props.subscript, int):
                limit = -field_props.subscript
                last_keys = last_keys[limit:]

            ctx_dict[field_props.name] = {k: v for k, v in nest_dict.items() if k in last_keys}

        await pac_writer(ctx_dict, created_at, updated_at, storage_key, primary_id)

        flattened_dict: List[Tuple[str, int, Dict]] = list()
        for field, payload in logs_dict.items():
            for key, value in payload.items():
                flattened_dict += [(field, key, value)]
        if len(flattened_dict) > 0:
            if not bool(chunk_size):
                await log_writer(flattened_dict, updated_at, primary_id)
            else:
                tasks = list()
                for ch in range(0, len(flattened_dict), chunk_size):
                    next_ch = ch + chunk_size
                    chunk = flattened_dict[ch:next_ch]
                    tasks += [log_writer(chunk, updated_at, primary_id)]
                if self.supports_async:
                    await gather(*tasks)
                else:
                    for task in tasks:
                        await task

        setattr(ctx, ExtraFields.primary_id.value, primary_id)
        setattr(ctx, ExtraFields.storage_key.value, storage_key)
