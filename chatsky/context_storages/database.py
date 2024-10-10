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

_SUBSCRIPT_TYPE = Union[Literal["__all__"], int, Set[str]]
_SUBSCRIPT_DICT = Dict[str, Union[_SUBSCRIPT_TYPE, Literal["__none__"]]]


class DBContextStorage(ABC):
    _main_table_name: Literal["main"] = "main"
    _turns_table_name: Literal["turns"] = "turns"
    _misc_table_name: Literal["misc"] = "misc"
    _key_column_name: Literal["key"] = "key"
    _value_column_name: Literal["value"] = "value"
    _id_column_name: Literal["id"] = "id"
    _current_turn_id_column_name: Literal["current_turn_id"] = "current_turn_id"
    _created_at_column_name: Literal["created_at"] = "created_at"
    _updated_at_column_name: Literal["updated_at"] = "updated_at"
    _framework_data_column_name: Literal["framework_data"] = "framework_data"
    _labels_field_name: Literal["labels"] = "labels"
    _requests_field_name: Literal["requests"] = "requests"
    _responses_field_name: Literal["responses"] = "responses"
    _misc_field_name: Literal["misc"] = "misc"
    _default_subscript_value: int = 3

    @property
    @abstractmethod
    def is_asynchronous(self) -> bool:
        return NotImplementedError

    def __init__(
        self,
        path: str,
        rewrite_existing: bool = False,
        configuration: Optional[_SUBSCRIPT_DICT] = None,
    ):
        _, _, file_path = path.partition("://")
        self.full_path = path
        """Full path to access the context storage, as it was provided by user."""
        self.path = Path(file_path)
        """`full_path` without a prefix defining db used."""
        self.rewrite_existing = rewrite_existing
        """Whether to rewrite existing data in the storage."""
        self._validate_subscripts(configuration if configuration is not None else dict())

    def _validate_subscripts(self, subscripts: _SUBSCRIPT_DICT) -> None:
        def get_subscript(name: str) -> _SUBSCRIPT_TYPE:
            value = subscripts.get(name, self._default_subscript_value)
            return 0 if value == "__none__" else value

        self.labels_subscript = get_subscript(self._labels_field_name)
        self.requests_subscript = get_subscript(self._requests_field_name)
        self.responses_subscript = get_subscript(self._responses_field_name)
        self.misc_subscript = get_subscript(self._misc_field_name)


    # TODO: this method (and similar) repeat often. Optimize?
    def _get_subscript_for_field(self, field_name: str) -> _SUBSCRIPT_TYPE:
        if field_name == self._labels_field_name:
            return self.labels_subscript
        elif field_name == self._requests_field_name:
            return self.requests_subscript
        elif field_name == self._responses_field_name:
            return self.responses_subscript
        elif field_name == self._misc_field_name:
            return self.misc_subscript
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
    async def delete_context(self, ctx_id: str) -> None:
        """
        Delete context from context storage.
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
    async def load_field_items(self, ctx_id: str, field_name: str, keys: List[Hashable]) -> List[Tuple[Hashable, bytes]]:
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
