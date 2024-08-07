"""
Database
--------
The `Database` module provides classes for managing the context storage of a dialog system.
The module can be used to store information such as the current state of the conversation
and other data. This module includes the intermediate class (:py:class:`.DBContextStorage`) is a class
that developers can inherit from in order to create their own context storage solutions.
This class implements the basic functionality and can be extended to add additional features as needed.
"""

import pickle
from abc import ABC, abstractmethod
from importlib import import_module
from typing import Any, Hashable, List, Literal, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from .protocol import PROTOCOLS


class FieldConfig(BaseModel, validate_assignment=True):
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


class DBContextStorage(ABC):
    _main_table_name: Literal["main"] = "main"
    _primary_id_column_name: Literal["primary_id"] = "primary_id"
    _created_at_column_name: Literal["created_at"] = "created_at"
    _updated_at_column_name: Literal["updated_at"] = "updated_at"
    _framework_data_column_name: Literal["framework_data"] = "framework_data"

    @property
    @abstractmethod
    def is_asynchronous(self) -> bool:
        return NotImplementedError

    def __init__(
        self,
        path: str,
        serializer: Optional[Any] = None,
        rewrite_existing: bool = False,
        turns_config: Optional[FieldConfig] = None,
        misc_config: Optional[FieldConfig] = None,
    ):
        _, _, file_path = path.partition("://")
        self.full_path = path
        """Full path to access the context storage, as it was provided by user."""
        self.path = file_path
        """`full_path` without a prefix defining db used."""
        self.serializer = pickle if serializer is None else serializer
        """Serializer that will be used with this storage (for serializing contexts in CONTEXT table)."""
        self.rewrite_existing = rewrite_existing
        """Whether to rewrite existing data in the storage."""
        self.turns_config = turns_config if turns_config is not None else FieldConfig(name="turns")
        self.misc_config = misc_config if misc_config is not None else FieldConfig(name="misc")

    @abstractmethod
    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, bytes]]:
        """
        Load main information about the context storage.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_main_info(self, ctx_id: str, crt_at: int, upd_at: int, fw_data: bytes) -> None:
        """
        Update main information about the context storage.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_main_info(self, ctx_id: str) -> None:
        """
        Delete main information about the context storage.
        """
        raise NotImplementedError

    @abstractmethod
    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[Hashable, bytes]]:
        """
        Load the latest field data.
        """
        raise NotImplementedError

    @abstractmethod
    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[Hashable]:
        """
        Load all field keys.
        """
        raise NotImplementedError

    @abstractmethod
    async def load_field_items(self, ctx_id: str, field_name: str, keys: Set[Hashable]) -> List[bytes]:
        """
        Load field items.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[Hashable, bytes]]) -> None:
        """
        Update field items.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_field_keys(self, ctx_id: str, field_name: str, keys: List[Hashable]) -> None:
        """
        Delete field keys.
        """
        raise NotImplementedError
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, DBContextStorage):
            return False
        return (
            self.full_path == other.full_path 
            and self.path == other.path
            and self._batch_size == other._batch_size
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
    If you want to use additional parameters in class constructors, you can pass them to this function as kwargs.

    :param path: Path to the file.
    """
    prefix, _, _ = path.partition("://")
    if "sql" in prefix:
        prefix = prefix.split("+")[0]  # this takes care of alternative sql drivers
    assert (
        prefix in PROTOCOLS
    ), f"""
    URI path should be prefixed with one of the following:\n
    {", ".join(PROTOCOLS.keys())}.\n
    For more information, see the function doc:\n{context_storage_factory.__doc__}
    """
    _class, module = PROTOCOLS[prefix]["class"], PROTOCOLS[prefix]["module"]
    target_class = getattr(import_module(f".{module}", package="chatsky.context_storages"), _class)
    return target_class(path, **kwargs)
