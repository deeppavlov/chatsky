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
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Hashable, List, Literal, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, field_validator, validate_call

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

    subscript: Union[Literal["__all__"], int, Set[str]] = 3
    """
    `subscript` is used for limiting keys for reading and writing.
    It can be a string `__all__` meaning all existing keys or number,
    string `__none__` meaning none of the existing keys (actually alias for 0),
    negative for first **N** keys and positive for last **N** keys.
    Keys should be sorted as numbers.
    Default: 3.
    """

    @field_validator("subscript", mode="before")
    @classmethod
    @validate_call
    def _validate_subscript(cls, subscript: Union[Literal["__all__"], Literal["__none__"], int, Set[str]]) -> Union[Literal["__all__"], int, Set[str]]:
        return 0 if subscript == "__none__" else subscript


class DBContextStorage(ABC):
    _main_table_name: Literal["main"] = "main"
    _turns_table_name: Literal["turns"] = "turns"
    _id_column_name: Literal["id"] = "id"
    _current_turn_id_column_name: Literal["current_turn_id"] = "current_turn_id"
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
        rewrite_existing: bool = False,
        configuration: Optional[Dict[str, FieldConfig]] = None,
    ):
        _, _, file_path = path.partition("://")
        self.full_path = path
        """Full path to access the context storage, as it was provided by user."""
        self.path = Path(file_path)
        """`full_path` without a prefix defining db used."""
        self.rewrite_existing = rewrite_existing
        """Whether to rewrite existing data in the storage."""
        configuration = configuration if configuration is not None else dict()
        self.labels_config = configuration.get("labels", FieldConfig(name="labels"))
        self.requests_config = configuration.get("requests", FieldConfig(name="requests"))
        self.responses_config = configuration.get("responses", FieldConfig(name="responses"))
        self.misc_config = configuration.get("misc", FieldConfig(name="misc"))

    def _get_config_for_field(self, field_name: str) -> FieldConfig:
        if field_name == self.labels_config.name:
            return self.labels_config
        elif field_name == self.requests_config.name:
            return self.requests_config
        elif field_name == self.responses_config.name:
            return self.responses_config
        elif field_name == self.misc_config.name:
            return self.misc_config
        else:
            raise ValueError(f"Unknown field name: {field_name}!")

    @abstractmethod
    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes]]:
        """
        Load main information about the context storage.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, fw_data: bytes) -> None:
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

    async def delete_field_keys(self, ctx_id: str, field_name: str, keys: List[Hashable]) -> None:
        """
        Delete field keys.
        """
        await self.update_field_items(ctx_id, field_name, [(k, None) for k in keys])

    @abstractmethod
    async def clear_all(self) -> None:
        """
        Clear all the chatsky tables and records.
        """
        raise NotImplementedError

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
        if "sql" in prefix:
            prefix = prefix.split("+")[0]  # this takes care of alternative sql drivers
        if prefix not in PROTOCOLS:
            raise ValueError(f"""
        URI path should be prefixed with one of the following:\n
        {", ".join(PROTOCOLS.keys())}.\n
        For more information, see the function doc:\n{context_storage_factory.__doc__}
        """)
        _class, module = PROTOCOLS[prefix]["class"], PROTOCOLS[prefix]["module"]
    target_class = getattr(import_module(f".{module}", package="chatsky.context_storages"), _class)
    return target_class(path, **kwargs)
