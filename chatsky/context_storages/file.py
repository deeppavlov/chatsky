"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows Chatsky to easily
store and retrieve context data.
"""

from abc import ABC, abstractmethod
import asyncio
from pickle import loads, dumps
from shelve import DbfilenameShelf
from typing import Any, List, Set, Tuple, Dict, Optional, Union

from pydantic import BaseModel, Field

from .database import ContextIdFilter, DBContextStorage, _SUBSCRIPT_DICT

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
    main: Dict[str, Tuple[int, int, int, bytes, bytes]] = Field(default_factory=dict)
    turns: List[Tuple[str, str, int, Optional[bytes]]] = Field(default_factory=list)


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
        configuration: Optional[_SUBSCRIPT_DICT] = None,
    ):
        DBContextStorage.__init__(self, path, rewrite_existing, configuration)
        asyncio.run(self._load())

    @abstractmethod
    async def _save(self, data: SerializableStorage) -> None:
        raise NotImplementedError

    @abstractmethod
    async def _load(self) -> SerializableStorage:
        raise NotImplementedError

    @DBContextStorage._convert_id_filter
    async def get_context_ids(self, filter: Union[ContextIdFilter, Dict[str, Any]]) -> Set[str]:
        return filter.filter_keys((await self._load()).main)

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes, bytes]]:
        return (await self._load()).main.get(ctx_id, None)

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, misc: bytes, fw_data: bytes) -> None:
        storage = await self._load()
        storage.main[ctx_id] = (turn_id, crt_at, upd_at, misc, fw_data)
        await self._save(storage)

    async def delete_context(self, ctx_id: str) -> None:
        storage = await self._load()
        storage.main.pop(ctx_id, None)
        storage.turns = [(c, f, k, v) for c, f, k, v in storage.turns if c != ctx_id]
        await self._save(storage)

    @DBContextStorage._verify_field_name
    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        storage = await self._load()
        select = sorted([(k, v) for c, f, k, v in storage.turns if c == ctx_id and f == field_name and v is not None], key=lambda e: e[0], reverse=True)
        if isinstance(self._subscripts[field_name], int):
            select = select[:self._subscripts[field_name]]
        elif isinstance(self._subscripts[field_name], Set):
            select = [(k, v) for k, v in select if k in self._subscripts[field_name]]
        return select

    @DBContextStorage._verify_field_name
    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[int]:
        return [k for c, f, k, v in (await self._load()).turns if c == ctx_id and f == field_name and v is not None]

    @DBContextStorage._verify_field_name
    async def load_field_items(self, ctx_id: str, field_name: str, keys: Set[int]) -> List[bytes]:
        return [(k, v) for c, f, k, v in (await self._load()).turns if c == ctx_id and f == field_name and k in keys and v is not None]

    @DBContextStorage._verify_field_name
    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[int, bytes]]) -> None:
        storage = await self._load()
        for k, v in items:
            upd = (ctx_id, field_name, k, v)
            for i in range(len(storage.turns)):
                if storage.turns[i][:-1] == upd[:-1]:
                    storage.turns[i] = upd
                    break
            else:
                storage.turns += [upd]
        await self._save(storage)

    async def clear_all(self) -> None:
        await self._save(SerializableStorage())


class JSONContextStorage(FileContextStorage):
    async def _save(self, data: SerializableStorage) -> None:
        if not await isfile(self.path) or (await stat(self.path)).st_size == 0:
            await makedirs(self.path.parent, exist_ok=True)
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
            await makedirs(self.path.parent, exist_ok=True)
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
        configuration: Optional[_SUBSCRIPT_DICT] = None,
    ):
        self._storage = None
        FileContextStorage.__init__(self, path, rewrite_existing, configuration)

    async def _save(self, data: SerializableStorage) -> None:
        self._storage[self._SHELVE_ROOT] = data.model_dump()

    async def _load(self) -> SerializableStorage:
        if self._storage is None:
            content = SerializableStorage()
            self._storage = DbfilenameShelf(str(self.path.absolute()), writeback=True)
            await self._save(content)
        else:
            content = SerializableStorage.model_validate(self._storage[self._SHELVE_ROOT])
        return content
