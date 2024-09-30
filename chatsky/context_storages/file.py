"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows Chatsky to easily
store and retrieve context data.
"""

from abc import ABC, abstractmethod
from pickle import loads, dumps
from shelve import DbfilenameShelf
from typing import List, Set, Tuple, Dict, Optional, Hashable

from pydantic import BaseModel, Field

from .database import DBContextStorage, FieldConfig


class SerializableStorage(BaseModel):
    main: Dict[str, Tuple[int, int, int, bytes]] = Field(default_factory=dict)
    turns: List[Tuple[str, str, int, Optional[bytes]]] = Field(default_factory=list)
    misc: List[Tuple[str, str, Optional[bytes]]] = Field(default_factory=list)


class FileContextStorage(DBContextStorage, ABC):
    """
    Implements :py:class:`.DBContextStorage` with `json` as the storage format.

    :param path: Target file URI. Example: `json://file.json`.
    :param context_schema: Context schema for this storage.
    :param serializer: Serializer that will be used for serializing contexts.
    """

    is_asynchronous = False

    def __init__(
        self, 
        path: str = "",
        rewrite_existing: bool = False,
        configuration: Optional[Dict[str, FieldConfig]] = None,
    ):
        DBContextStorage.__init__(self, path, rewrite_existing, configuration)
        self._load()

    @abstractmethod
    def _save(self, data: SerializableStorage) -> None:
        raise NotImplementedError

    @abstractmethod
    def _load(self) -> SerializableStorage:
        raise NotImplementedError

    async def _get_elems_for_field_name(self, ctx_id: str, field_name: str) -> List[Tuple[Hashable, bytes]]:
        storage = self._load()
        if field_name == self.misc_config.name:
            return [(k, v) for c, k, v in storage.misc if c == ctx_id]
        elif field_name in (self.labels_config.name, self.requests_config.name, self.responses_config.name):
            return [(k, v) for c, f, k, v in storage.turns if c == ctx_id and f == field_name ]
        else:
            raise ValueError(f"Unknown field name: {field_name}!")

    def _get_table_for_field_name(self, storage: SerializableStorage, field_name: str) -> List[Tuple]:
        if field_name == self.misc_config.name:
            return storage.misc
        elif field_name in (self.labels_config.name, self.requests_config.name, self.responses_config.name):
            return storage.turns
        else:
            raise ValueError(f"Unknown field name: {field_name}!")

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes]]:
        return self._load().main.get(ctx_id, None)

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, fw_data: bytes) -> None:
        storage = self._load()
        storage.main[ctx_id] = (turn_id, crt_at, upd_at, fw_data)
        self._save(storage)

    async def delete_main_info(self, ctx_id: str) -> None:
        storage = self._load()
        storage.main.pop(ctx_id, None)
        storage.turns = [(c, f, k, v) for c, f, k, v in storage.turns if c != ctx_id]
        storage.misc = [(c, k, v) for c, k, v in storage.misc if c != ctx_id]
        self._save(storage)

    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[Hashable, bytes]]:
        config = self._get_config_for_field(field_name)
        select = await self._get_elems_for_field_name(ctx_id, field_name)
        if field_name != self.misc_config.name:
            select = sorted(select, key=lambda e: e[0], reverse=True)
        if isinstance(config.subscript, int):
            select = select[:config.subscript]
        elif isinstance(config.subscript, Set):
            select = [(k, v) for k, v in select if k in config.subscript]
        return select

    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[Hashable]:
        return [k for k, _ in await self._get_elems_for_field_name(ctx_id, field_name)]

    async def load_field_items(self, ctx_id: str, field_name: str, keys: Set[Hashable]) -> List[bytes]:
        return [v for k, v in await self._get_elems_for_field_name(ctx_id, field_name) if k in keys]

    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[Hashable, bytes]]) -> None:
        storage = self._load()
        table = self._get_table_for_field_name(storage, field_name)
        for k, v in items:
            upd = (ctx_id, k, v) if field_name == self.misc_config.name else (ctx_id, field_name, k, v)
            for i in range(len(table)):
                if table[i][:-1] == upd[:-1]:
                    table[i] = upd
                    break
            else:
                table += [upd]
        self._save(storage)

    async def clear_all(self) -> None:
        self._save(SerializableStorage())


class JSONContextStorage(FileContextStorage):
    def _save(self, data: SerializableStorage) -> None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(data.model_dump_json(), encoding="utf-8")

    def _load(self) -> SerializableStorage:
        if not self.path.exists() or self.path.stat().st_size == 0:
            storage = SerializableStorage()
            self._save(storage)
        else:
            storage = SerializableStorage.model_validate_json(self.path.read_text(encoding="utf-8"))
        return storage


class PickleContextStorage(FileContextStorage):
    def _save(self, data: SerializableStorage) -> None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(dumps(data.model_dump()))

    def _load(self) -> SerializableStorage:
        if not self.path.exists() or self.path.stat().st_size == 0:
            storage = SerializableStorage()
            self._save(storage)
        else:
            storage = SerializableStorage.model_validate(loads(self.path.read_bytes()))
        return storage


class ShelveContextStorage(FileContextStorage):
    _SHELVE_ROOT = "root"

    def __init__(
        self, 
        path: str = "",
        rewrite_existing: bool = False,
        configuration: Optional[Dict[str, FieldConfig]] = None,
    ):
        self._storage = None
        FileContextStorage.__init__(self, path, rewrite_existing, configuration)

    def _save(self, data: SerializableStorage) -> None:
        self._storage[self._SHELVE_ROOT] = data.model_dump()

    def _load(self) -> SerializableStorage:
        if self._storage is None:
            content = SerializableStorage()
            self._storage = DbfilenameShelf(str(self.path.absolute()), writeback=True)
            self._save(content)
        else:
            content = SerializableStorage.model_validate(self._storage[self._SHELVE_ROOT])
        return content
