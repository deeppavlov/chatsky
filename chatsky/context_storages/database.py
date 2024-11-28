"""
Database
--------
The `Database` module provides classes for managing the context storage of a dialog system.
The module can be used to store information such as the current state of the conversation
and other data. This module includes the intermediate class (:py:class:`.DBContextStorage`) is a class
that developers can inherit from in order to create their own context storage solutions.
This class implements the basic functionality and can be extended to add additional features as needed.
"""

from abc import ABC, abstractmethod
from asyncio import Lock
from functools import wraps
from importlib import import_module
from logging import getLogger
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, Set, Tuple, Union

from chatsky.utils.logging import collapse_num_list

from .protocol import PROTOCOLS

_SUBSCRIPT_TYPE = Union[Literal["__all__"], int, Set[str]]
_SUBSCRIPT_DICT = Dict[str, Union[_SUBSCRIPT_TYPE]]

logger = getLogger(__name__)


class NameConfig:
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


class DBContextStorage(ABC):
    _default_subscript_value: int = 3

    def __init__(
        self,
        path: str,
        rewrite_existing: bool = False,
        configuration: Optional[_SUBSCRIPT_DICT] = None,
    ):
        _, _, file_path = path.partition("://")
        configuration = configuration if configuration is not None else dict()
        self.full_path = path
        """Full path to access the context storage, as it was provided by user."""
        self.path = Path(file_path)
        """`full_path` without a prefix defining db used."""
        self.rewrite_existing = rewrite_existing
        """Whether to rewrite existing data in the storage."""
        self._subscripts = dict()
        self._sync_lock = Lock()
        self.connected = False
        for field in (NameConfig._labels_field, NameConfig._requests_field, NameConfig._responses_field):
            value = configuration.get(field, self._default_subscript_value)
            if (not isinstance(value, int)) or value >= 1:
                self._subscripts[field] = value
            else:
                raise ValueError(f"Invalid subscript value ({value}) for field {field}")

    @property
    @abstractmethod
    def is_concurrent(self) -> bool:
        raise NotImplementedError

    @staticmethod
    def _lock(function: Callable[..., Awaitable[Any]]):
        @wraps(function)
        async def wrapped(self, *args, **kwargs):
            if not self.is_concurrent:
                async with self._sync_lock:
                    return await function(self, *args, **kwargs)
            else:
                return await function(self, *args, **kwargs)

        return wrapped

    @classmethod
    def _validate_field_name(cls, field_name: str) -> str:
        if field_name not in (NameConfig._labels_field, NameConfig._requests_field, NameConfig._responses_field):
            raise ValueError(f"Invalid value '{field_name}' for argument 'field_name'!")
        else:
            return field_name

    async def connect(self) -> None:
        self.connected = True

    @abstractmethod
    async def _load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes, bytes]]:
        raise NotImplementedError

    @_lock
    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes, bytes]]:
        """
        Load main information about the context.
        """
        if not self.connected:
            logger.debug(f"Connecting to context storage {type(self).__name__} ...")
            await self.connect()
        logger.debug(f"Loading main info for {ctx_id}...")
        result = await self._load_main_info(ctx_id)
        logger.debug(f"Main info loaded for {ctx_id}")
        return result

    @abstractmethod
    async def _update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, misc: bytes, fw_data: bytes) -> None:
        raise NotImplementedError

    @_lock
    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, misc: bytes, fw_data: bytes) -> None:
        """
        Update main information about the context.
        """
        if not self.connected:
            logger.debug(f"Connecting to context storage {type(self).__name__} ...")
            await self.connect()
        logger.debug(f"Updating main info for {ctx_id}...")
        await self._update_main_info(ctx_id, turn_id, crt_at, upd_at, misc, fw_data)
        logger.debug(f"Main info updated for {ctx_id}")

    @abstractmethod
    async def _delete_context(self, ctx_id: str) -> None:
        raise NotImplementedError

    @_lock
    async def delete_context(self, ctx_id: str) -> None:
        """
        Delete context from context storage.
        """
        if not self.connected:
            logger.debug(f"Connecting to context storage {type(self).__name__} ...")
            await self.connect()
        logger.debug(f"Deleting context {ctx_id}...")
        await self._delete_context(ctx_id)
        logger.debug(f"Context {ctx_id} deleted")

    @abstractmethod
    async def _load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        raise NotImplementedError

    @_lock
    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        """
        Load the latest field data.
        """
        if not self.connected:
            logger.debug(f"Connecting to context storage {type(self).__name__} ...")
            await self.connect()
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
        """
        if not self.connected:
            logger.debug(f"Connecting to context storage {type(self).__name__} ...")
            await self.connect()
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
        Load field items.
        """
        if not self.connected:
            logger.debug(f"Connecting to context storage {type(self).__name__} ...")
            await self.connect()
        logger.debug(f"Loading field items for {ctx_id}, {field_name} ({collapse_num_list(keys)})...")
        result = await self._load_field_items(ctx_id, self._validate_field_name(field_name), keys)
        logger.debug(f"Field items loaded for {ctx_id}, {field_name}: {collapse_num_list([k for k, _ in result])}")
        return result

    @abstractmethod
    async def _update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[int, Optional[bytes]]]) -> None:
        raise NotImplementedError

    @_lock
    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[int, Optional[bytes]]]) -> None:
        """
        Update field items.
        """
        if len(items) == 0:
            logger.debug(f"No fields to update in {ctx_id}, {field_name}!")
            return
        elif not self.connected:
            logger.debug(f"Connecting to context storage {type(self).__name__} ...")
            await self.connect()
        logger.debug(f"Updating fields for {ctx_id}, {field_name}: {collapse_num_list(list(k for k, _ in items))}...")
        await self._update_field_items(ctx_id, self._validate_field_name(field_name), items)
        logger.debug(f"Fields updated for {ctx_id}, {field_name}")

    @_lock
    async def delete_field_keys(self, ctx_id: str, field_name: str, keys: List[int]) -> None:
        """
        Delete field keys.
        """
        if len(keys) == 0:
            logger.debug(f"No fields to delete in {ctx_id}, {field_name}!")
            return
        elif not self.connected:
            logger.debug(f"Connecting to context storage {type(self).__name__} ...")
            await self.connect()
        logger.debug(f"Deleting fields for {ctx_id}, {field_name}: {collapse_num_list(keys)}...")
        await self._update_field_items(ctx_id, self._validate_field_name(field_name), [(k, None) for k in keys])
        logger.debug(f"Fields deleted for {ctx_id}, {field_name}")

    @abstractmethod
    async def _clear_all(self) -> None:
        raise NotImplementedError

    @_lock
    async def clear_all(self) -> None:
        """
        Clear all the chatsky tables and records.
        """
        if not self.connected:
            logger.debug(f"Connecting to context storage {type(self).__name__} ...")
            await self.connect()
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
