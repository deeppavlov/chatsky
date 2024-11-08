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
from typing import List, Set, Tuple, Dict, Optional
import logging

from pydantic import BaseModel, Field

from .database import DBContextStorage, _SUBSCRIPT_DICT, _SUBSCRIPT_TYPE
from chatsky.utils.logging import collapse_num_list

try:
    from aiofiles import open
    from aiofiles.os import stat, makedirs
    from aiofiles.ospath import isfile

    json_available = True
    pickle_available = True
except ImportError:
    json_available = False
    pickle_available = False


logger = logging.getLogger(__name__)


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

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes, bytes]]:
        logger.debug(f"Loading main info for {ctx_id}...")
        result = (await self._load()).main.get(ctx_id, None)
        logger.debug(f"Main info loaded for {ctx_id}")
        return result

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, misc: bytes, fw_data: bytes) -> None:
        logger.debug(f"Updating main info for {ctx_id}...")
        storage = await self._load()
        storage.main[ctx_id] = (turn_id, crt_at, upd_at, misc, fw_data)
        await self._save(storage)
        logger.debug(f"Main info updated for {ctx_id}")

    async def delete_context(self, ctx_id: str) -> None:
        logger.debug(f"Deleting context {ctx_id}...")
        storage = await self._load()
        storage.main.pop(ctx_id, None)
        storage.turns = [(c, f, k, v) for c, f, k, v in storage.turns if c != ctx_id]
        await self._save(storage)
        logger.debug(f"Context {ctx_id} deleted")

    @DBContextStorage._verify_field_name
    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        logger.debug(f"Loading latest items for {ctx_id}, {field_name}...")
        storage = await self._load()
        select = sorted([(k, v) for c, f, k, v in storage.turns if c == ctx_id and f == field_name and v is not None], key=lambda e: e[0], reverse=True)
        if isinstance(self._subscripts[field_name], int):
            select = select[:self._subscripts[field_name]]
        elif isinstance(self._subscripts[field_name], Set):
            select = [(k, v) for k, v in select if k in self._subscripts[field_name]]
        logger.debug(f"Latest field loaded for {ctx_id}, {field_name}: {collapse_num_list(list(k for k, _ in select))}")
        return select

    @DBContextStorage._verify_field_name
    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[int]:
        logger.debug(f"Loading field keys for {ctx_id}, {field_name}...")
        result = [k for c, f, k, v in (await self._load()).turns if c == ctx_id and f == field_name and v is not None]
        logger.debug(f"Field keys loaded for {ctx_id}, {field_name}: {collapse_num_list(result)}")
        return result

    @DBContextStorage._verify_field_name
    async def load_field_items(self, ctx_id: str, field_name: str, keys: List[int]) -> List[bytes]:
        logger.debug(f"Loading field items for {ctx_id}, {field_name} ({collapse_num_list(keys)})...")
        result = [(k, v) for c, f, k, v in (await self._load()).turns if c == ctx_id and f == field_name and k in keys and v is not None]
        logger.debug(f"Field items loaded for {ctx_id}, {field_name}: {collapse_num_list([k for k, _ in result])}")
        return result

    @DBContextStorage._verify_field_name
    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[int, bytes]]) -> None:
        logger.debug(f"Updating fields for {ctx_id}, {field_name}: {collapse_num_list(list(k for k, _ in items))}...")
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
        logger.debug(f"Fields updated for {ctx_id}, {field_name}")

    async def clear_all(self) -> None:
        logger.debug("Clearing all")
        await self._save(SerializableStorage())


class JSONContextStorage(FileContextStorage):
    @DBContextStorage._synchronously_lock
    async def _save(self, data: SerializableStorage) -> None:
        if not await isfile(self.path) or (await stat(self.path)).st_size == 0:
            await makedirs(self.path.parent, exist_ok=True)
        async with open(self.path, "w", encoding="utf-8") as file_stream:
            await file_stream.write(data.model_dump_json())

    @DBContextStorage._synchronously_lock
    async def _load(self) -> SerializableStorage:
        if not await isfile(self.path) or (await stat(self.path)).st_size == 0:
            storage = SerializableStorage()
            await self._save(storage)
        else:
            async with open(self.path, "r", encoding="utf-8") as file_stream:
                storage = SerializableStorage.model_validate_json(await file_stream.read())
        return storage


class PickleContextStorage(FileContextStorage):
    @DBContextStorage._synchronously_lock
    async def _save(self, data: SerializableStorage) -> None:
        if not await isfile(self.path) or (await stat(self.path)).st_size == 0:
            await makedirs(self.path.parent, exist_ok=True)
        async with open(self.path, "wb") as file_stream:
            await file_stream.write(dumps(data.model_dump()))

    @DBContextStorage._synchronously_lock
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

    @DBContextStorage._synchronously_lock
    async def _save(self, data: SerializableStorage) -> None:
        self._storage[self._SHELVE_ROOT] = data.model_dump()

    @DBContextStorage._synchronously_lock
    async def _load(self) -> SerializableStorage:
        if self._storage is None:
            content = SerializableStorage()
            self._storage = DbfilenameShelf(str(self.path.absolute()), writeback=True)
            await self._save(content)
        else:
            content = SerializableStorage.model_validate(self._storage[self._SHELVE_ROOT])
        return content
