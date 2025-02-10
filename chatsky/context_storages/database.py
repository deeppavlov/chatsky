"""
Database
--------
The `Database` module provides classes for managing the context storage of a dialog system.
The module can be used to store information such as the current state of the conversation
and other data. This module includes the intermediate class (:py:class:`.DBContextStorage`) is a class
that developers can inherit from in order to create their own context storage solutions.
This class implements the basic functionality and can be extended to add additional features as needed.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from asyncio import Lock
from json import loads
from functools import wraps
from importlib import import_module
from logging import getLogger
from pathlib import Path
from time import time_ns
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field, PrivateAttr, TypeAdapter, field_serializer, field_validator

from chatsky.utils.logging import collapse_num_list

from .protocol import PROTOCOLS

if TYPE_CHECKING:
    from chatsky.core.context import FrameworkData

_SUBSCRIPT_TYPE = Union[Literal["__all__"], int]
_SUBSCRIPT_DICT = Dict[Literal["labels", "requests", "responses"], Union[_SUBSCRIPT_TYPE]]

logger = getLogger(__name__)


class NameConfig:
    """
    Configuration of names of different database parts,
    including table names, column names, field names, etc.
    """

    _main_table: Literal["main"] = "main"
    _turns_table: Literal["turns"] = "turns"
    _key_column: Literal["key"] = "key"
    _id_column: Literal["id"] = "id"
    _current_turn_id_column: Literal["current_turn_id"] = "current_turn_id"
    _created_at_column: Literal["created_at"] = "created_at"
    _updated_at_column: Literal["updated_at"] = "updated_at"
    _misc_column: Literal["misc"] = "misc"
    _framework_data_column: Literal["framework_data"] = "framework_data"
    _labels_field: Literal["labels"] = "labels"
    _requests_field: Literal["requests"] = "requests"
    _responses_field: Literal["responses"] = "responses"


class ContextInfo(BaseModel):
    """
    Main context fields, that are stored in `MAIN` table.
    For most of the database backends, it will be serialized to json.
    For SQL database backends, it will be written to different table columns.
    For memory context storage, it won't be serialized at all.
    """

    turn_id: int
    created_at: int = Field(default_factory=time_ns)
    updated_at: int = Field(default_factory=time_ns)
    misc: Dict[str, Any] = Field(default_factory=dict)
    framework_data: FrameworkData = Field(default_factory=dict, validate_default=True)

    _misc_adaptor: TypeAdapter[Dict[str, Any]] = PrivateAttr(default=TypeAdapter(Dict[str, Any]))

    @field_validator("framework_data", "misc", mode="before")
    @classmethod
    def _validate_framework_data(cls, value: Any) -> Dict:
        if isinstance(value, bytes) or isinstance(value, str):
            value = loads(value)
        return value

    @field_serializer("misc", when_used="always")
    def _serialize_misc(self, misc: Dict[str, Any]) -> bytes:
        return self._misc_adaptor.dump_json(misc)

    @field_serializer("framework_data", when_used="always")
    def _serialize_framework_data(self, framework_data: FrameworkData) -> bytes:
        return framework_data.model_dump_json().encode()

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, BaseModel):
            return self.model_dump() == other.model_dump()
        return super().__eq__(other)


def _lock(function: Callable[..., Awaitable[Any]]):
    @wraps(function)
    async def wrapped(self: DBContextStorage, *args, **kwargs):
        if not self.connected:
            logger.warning(
                "Initializing ContextStorage in-place, that is NOT thread-safe and in general should be avoided!"
            )
            await self.connect()
        if not self.is_concurrent:
            async with self._sync_lock:
                return await function(self, *args, **kwargs)
        else:
            return await function(self, *args, **kwargs)

    return wrapped


class DBContextStorage(ABC):
    """
    Base context storage class.
    Includes a set of methods for storing and reading different context parts.

    :param path: Path to the storage instance.
    :param rewrite_existing: Whether `TURNS` modified locally should be updated in database or not.
    :param partial_read_config: Dictionary of subscripts for all possible turn items.
    """

    _default_subscript_value: int = 3

    def __init__(
        self,
        path: str,
        rewrite_existing: bool = False,
        partial_read_config: Optional[_SUBSCRIPT_DICT] = None,
    ):
        _, _, file_path = path.partition("://")
        configuration = partial_read_config if partial_read_config is not None else dict()

        self.full_path = path
        """
        Full path to access the context storage, as it was provided by user.
        """

        self.path = Path(file_path)
        """
        `full_path` without a prefix defining db used.
        """

        self.rewrite_existing = rewrite_existing
        """
        Whether to rewrite existing data in the storage.
        """

        self._subscripts = dict()
        """
        Subscripts control how many elements will be loaded from the database.
        Can be an integer, meaning the number of *last* elements to load.
        A special value for loading all the elements at once: "__all__".
        Can also be a set of keys that should be loaded.
        """

        self._sync_lock = None
        """
        Synchronization lock for the databases that don't support
        asynchronous atomic reads and writes.
        """

        self.connected = False
        """
        Flag that marks if the storage is connected to the backend.
        Should be set in `pipeline.run` or later (lazily).
        """

        for field in (NameConfig._labels_field, NameConfig._requests_field, NameConfig._responses_field):
            value = configuration.get(field, self._default_subscript_value)
            if (not isinstance(value, int)) or value >= 1:
                self._subscripts[field] = value
            else:
                raise ValueError(f"Invalid subscript value ({value}) for field {field}")

    @property
    @abstractmethod
    def is_concurrent(self) -> bool:
        """
        If the database backend support asynchronous IO.
        """

        raise NotImplementedError

    @classmethod
    def _validate_field_name(cls, field_name: str) -> str:
        if field_name not in (NameConfig._labels_field, NameConfig._requests_field, NameConfig._responses_field):
            raise ValueError(f"Invalid value '{field_name}' for argument 'field_name'!")
        else:
            return field_name

    @abstractmethod
    async def _connect(self) -> None:
        raise NotImplementedError

    async def connect(self) -> None:
        """
        Connect to the backend context storage.
        """

        logger.info(f"Connecting to context storage {type(self).__name__} ...")
        await self._connect()
        self._sync_lock = Lock()
        self.connected = True

    @abstractmethod
    async def _load_main_info(self, ctx_id: str) -> Optional[ContextInfo]:
        raise NotImplementedError

    @_lock
    async def load_main_info(self, ctx_id: str) -> Optional[ContextInfo]:
        """
        Load main information about the context.

        :param ctx_id: Context identifier.
        :return: Context main information (from `MAIN` table).
        """

        logger.debug(f"Loading main info for {ctx_id}...")
        result = await self._load_main_info(ctx_id)
        logger.debug(f"Main info loaded for {ctx_id}")
        return result

    @abstractmethod
    async def _update_context(self, ctx_id: str, ctx_info: ContextInfo, field_info: List[Tuple[str, List[Tuple[int, Optional[bytes]]]]]) -> None:
        raise NotImplementedError

    @_lock
    async def update_context(self, ctx_id: str, ctx_info: ContextInfo, field_info: List[Tuple[str, List[Tuple[int, bytes]], List[int]]]) -> None:
        """
        Update context intofrmation.

        :param ctx_id: Context identifier.
        :param ctx_info: Context information (will be written to different tables at once).
        """

        joined_field_info = list()
        logger.debug(f"Updating context for {ctx_id}...")
        for field, added, deleted in field_info:
            field = self._validate_field_name(field)
            if len(added) == 0:
                logger.debug(f"\tNo fields to add in {field}!")
            else:
                joined_field_info += [(field, added)]
                logger.debug(f"\tAdding fields for {field}: {collapse_num_list(list(k for k, _ in added))}...")
            if len(deleted) == 0:
                logger.debug(f"\tNo fields to delete in {field}!")
            else:
                joined_field_info += [(field, [(k, None) for k in deleted])]
                logger.debug(f"\tDeleting fields for {field}: {collapse_num_list(deleted)}...")
        await self._update_context(ctx_id, ctx_info, joined_field_info)
        logger.debug(f"Context updated for {ctx_id}")

    @abstractmethod
    async def _delete_context(self, ctx_id: str) -> None:
        raise NotImplementedError

    @_lock
    async def delete_context(self, ctx_id: str) -> None:
        """
        Delete context from context storage.

        :param ctx_id: Context identifier.
        """

        logger.debug(f"Deleting context {ctx_id}...")
        await self._delete_context(ctx_id)
        logger.debug(f"Context {ctx_id} deleted")

    @abstractmethod
    async def _load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        raise NotImplementedError

    @_lock
    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        """
        Load the latest field data (specified by `subscript` value).

        :param ctx_id: Context identifier.
        :param field_name: Field name to load from `TURNS` table.
        :return: List of tuples (step number, serialized value).
        """

        logger.debug(f"Loading latest items for {ctx_id}, {field_name}...")
        result = await self._load_field_latest(ctx_id, self._validate_field_name(field_name))
        logger.debug(f"Latest field loaded for {ctx_id}, {field_name}: {collapse_num_list(list(k for k, _ in result))}")
        return result

    @abstractmethod
    async def _load_field_keys(self, ctx_id: str, field_name: str) -> List[int]:
        raise NotImplementedError

    @_lock
    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[int]:
        """
        Load all field keys.

        :param ctx_id: Context identifier.
        :param field_name: Field name to load from `TURNS` table.
        :return: List of all the step numbers.
        """

        logger.debug(f"Loading field keys for {ctx_id}, {field_name}...")
        result = await self._load_field_keys(ctx_id, self._validate_field_name(field_name))
        logger.debug(f"Field keys loaded for {ctx_id}, {field_name}: {collapse_num_list(result)}")
        return result

    @abstractmethod
    async def _load_field_items(self, ctx_id: str, field_name: str, keys: List[int]) -> List[Tuple[int, bytes]]:
        raise NotImplementedError

    @_lock
    async def load_field_items(self, ctx_id: str, field_name: str, keys: List[int]) -> List[Tuple[int, bytes]]:
        """
        Load field items (specified by key list).
        The items that are equal to `None` will be ignored.

        :param ctx_id: Context identifier.
        :param field_name: Field name to load from `TURNS` table.
        :param keys: List of keys to load.
        :return: List of tuples (step number, serialized value).
        """

        logger.debug(f"Loading field items for {ctx_id}, {field_name} ({collapse_num_list(keys)})...")
        result = await self._load_field_items(ctx_id, self._validate_field_name(field_name), keys)
        logger.debug(f"Field items loaded for {ctx_id}, {field_name}: {collapse_num_list([k for k, _ in result])}")
        return result

    @abstractmethod
    async def _clear_all(self) -> None:
        raise NotImplementedError

    @_lock
    async def clear_all(self) -> None:
        """
        Clear all the chatsky tables and records.
        """

        logger.debug("Clearing all")
        await self._clear_all()

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, DBContextStorage):
            return False
        return (
            self.full_path == other.full_path
            and self.path == other.path
            and self.rewrite_existing == other.rewrite_existing
        )


def context_storage_factory(path: str, **kwargs) -> DBContextStorage:
    """
    Use context_storage_factory to lazy import context storage types and instantiate them.
    The function takes a database connection URI or its equivalent. It should be prefixed with database name,
    followed by the symbol triplet '://'.

    Then, you should list the connection parameters like this: user:password@host:port/database
    The whole URI will then look like this:

    - shelve://path_to_the_file/file_name
    - json://path_to_the_file/file_name
    - pickle://path_to_the_file/file_name
    - sqlite+aiosqlite://path_to_the_file/file_name
    - redis://:pass@localhost:6378/0
    - mongodb://admin:pass@localhost:27016/admin
    - mysql+asyncmy://root:pass@localhost:3306/test
    - postgresql+asyncpg://postgres:pass@localhost:5430/test
    - grpc://localhost:2134/local
    - grpcs://localhost:2134/local

    For context storages that write to local files, the function expects a file path instead of connection params:
    json://file.json
    When using sqlite backend your prefix should contain three slashes if you use Windows, or four in other cases:
    sqlite:////file.db

    For MemoryContextStorage pass an empty string as ``path``.

    If you want to use additional parameters in class constructors, you can pass them to this function as kwargs.

    :param path: Path to the file.
    """

    if path == "":
        module = "memory"
        _class = "MemoryContextStorage"
    else:
        prefix, _, _ = path.partition("://")
        if any(prefix.startswith(sql_prefix) for sql_prefix in ("sqlite", "mysql", "postgresql")):
            prefix = prefix.split("+")[0]  # this takes care of alternative sql drivers
        if prefix not in PROTOCOLS:
            raise ValueError(
                f"""
        URI path should be prefixed with one of the following:\n
        {", ".join(PROTOCOLS.keys())}.\n
        For more information, see the function doc:\n{context_storage_factory.__doc__}
        """
            )
        _class, module = PROTOCOLS[prefix]["class"], PROTOCOLS[prefix]["module"]
    target_class = getattr(import_module(f".{module}", package="chatsky.context_storages"), _class)
    return target_class(path, **kwargs)
