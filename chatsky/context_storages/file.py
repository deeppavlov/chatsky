"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows Chatsky to easily
store and retrieve context data.
"""

from abc import ABC, abstractmethod
import asyncio
from pathlib import Path
from pickle import loads, dumps
from shelve import DbfilenameShelf
from typing import List, Set, Tuple, Dict, Optional, Hashable

from pydantic import BaseModel, Field

from .database import DBContextStorage, FieldConfig

try:
    from aiofiles import open
    from aiofiles.os import stat, makedirs
    from aiofiles.ospath import isfile

    json_available = True
    pickle_available = True
except ImportError:
    json_available = False
    pickle_available = False


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
        asyncio.run(self._load())

    @abstractmethod
    async def _save(self, data: SerializableStorage) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _load(self) -> SerializableStorage:
        raise NotImplementedError

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes]]:
        return (await self._load()).main.get(ctx_id, None)

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, fw_data: bytes) -> None:
        storage = await self._load()
        storage.main[ctx_id] = (turn_id, crt_at, upd_at, fw_data)
        await self._save(storage)

    async def delete_main_info(self, ctx_id: str) -> None:
        storage = await self._load()
        storage.main.pop(ctx_id, None)
        storage.turns = [t for t in storage.turns if t[0] != ctx_id]
        storage.misc = [m for m in storage.misc if m[0] != ctx_id]
        await self._save(storage)

    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[Hashable, bytes]]:
        storage = await self._load()
        if field_name == self.misc_config.name:
            select = [m for m in storage.misc if m[0] == ctx_id]
            config = self.misc_config
        elif field_name in (self.labels_config.name, self.requests_config.name, self.responses_config.name):
            select = [t for t in storage.turns if t[0] == ctx_id and t[1] == field_name]
            select = sorted(select, key=lambda x: x[2], reverse=True)
            config = [c for c in (self.labels_config, self.requests_config, self.responses_config) if c.name == field_name][0]
        else:
            raise ValueError(f"Unknown field name: {field_name}!")
        if isinstance(config.subscript, int):
            select = select[:config.subscript]
        elif isinstance(config.subscript, Set):
            select = [e for e in select if e[1] in config.subscript]
        return [(e[-2], e[-1]) for e in select]

    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[Hashable]:
        storage = await self._load()
        if field_name == self.misc_config.name:
            return [m[1] for m in storage.misc if m[0] == ctx_id]
        elif field_name in (self.labels_config.name, self.requests_config.name, self.responses_config.name):
            return [t[2] for t in storage.turns if t[0] == ctx_id and t[1] == field_name]
        else:
            raise ValueError(f"Unknown field name: {field_name}!")

    async def load_field_items(self, ctx_id: str, field_name: str, keys: Set[Hashable]) -> List[bytes]:
        storage = await self._load()
        if field_name == self.misc_config.name:
            return [m[2] for m in storage.misc if m[0] == ctx_id and m[1] in keys]
        elif field_name in (self.labels_config.name, self.requests_config.name, self.responses_config.name):
            return [t[3] for t in storage.turns if t[0] == ctx_id and t[1] == field_name and t[2] in keys]
        else:
            raise ValueError(f"Unknown field name: {field_name}!")

    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[Hashable, bytes]]) -> None:
        storage = await self._load()
        while len(items) > 0:
            nx = items.pop(0)
            if field_name == self.misc_config.name:
                upd = (ctx_id, nx[0], nx[1])
                for i in range(len(storage.misc)):
                    if storage.misc[i][0] == ctx_id and storage.misc[i][-2] == nx[0]:
                        storage.misc[i] = upd
                        break
                else:
                    storage.misc += [upd]
            elif field_name in (self.labels_config.name, self.requests_config.name, self.responses_config.name):
                upd = (ctx_id, field_name, nx[0], nx[1])
                for i in range(len(storage.turns)):
                    if storage.turns[i][0] == ctx_id and storage.turns[i][1] == field_name and storage.turns[i][-2] == nx[0]:
                        storage.turns[i] = upd
                        break
                else:
                    storage.turns += [upd]
            else:
                raise ValueError(f"Unknown field name: {field_name}!")
        await self._save(storage)

    async def clear_all(self) -> None:
        await self._save(SerializableStorage())


class JSONContextStorage(FileContextStorage):
    async def _save(self, data: SerializableStorage) -> None:
        if not await isfile(self.path) or (await stat(self.path)).st_size == 0:
            await makedirs(Path(self.path).parent, exist_ok=True)
        async with open(self.path, "w", encoding="utf-8") as file_stream:
            await file_stream.write(data.model_dump_json())

    async def _load(self) -> SerializableStorage:
        if not await isfile(self.path) or (await stat(self.path)).st_size == 0:
            storage = SerializableStorage()
            await self._save(storage)
        else:
            async with open(self.path, "r", encoding="utf-8") as file_stream:
                storage = SerializableStorage.model_validate_json(await file_stream.read())
        return storage


class PickleContextStorage(FileContextStorage):
    async def _save(self, data: SerializableStorage) -> None:
        if not await isfile(self.path) or (await stat(self.path)).st_size == 0:
            await makedirs(Path(self.path).parent, exist_ok=True)
        async with open(self.path, "wb") as file_stream:
            await file_stream.write(dumps(data.model_dump()))

    async def _load(self) -> SerializableStorage:
        if not await isfile(self.path) or (await stat(self.path)).st_size == 0:
            storage = SerializableStorage()
            await self._save(storage)
        else:
            async with open(self.path, "rb") as file_stream:
                storage = SerializableStorage.model_validate(loads(await file_stream.read()))
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

    async def _save(self, data: SerializableStorage) -> None:
        self._storage[self._SHELVE_ROOT] = data.model_dump()

    async def _load(self) -> SerializableStorage:
        if self._storage is None:
            content = SerializableStorage()
            self._storage = DbfilenameShelf(self.path, writeback=True)
            await self._save(content)
        else:
            content = SerializableStorage.model_validate(self._storage[self._SHELVE_ROOT])
        return content
