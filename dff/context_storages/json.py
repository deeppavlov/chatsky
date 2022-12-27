"""
json
---------------------------
Provides the json-based version of the :py:class:`.DBContextStorage`.
"""
import asyncio
from typing import Any

import aiofiles
import aiofiles.os
from pydantic import BaseModel, Extra, root_validator

from .database import DBContextStorage, threadsafe_method
from dff.script import Context


class SerializeableStorage(BaseModel, extra=Extra.allow):
    @root_validator
    def validate_any(cls, vals):
        for key, value in vals.items():
            vals[key] = Context.cast(value)
        return vals


class JSONContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `json` as the storage format.

    Parameters
    -----------

    path: str
        Target file URI. Example: 'json://file.json'
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)

        asyncio.run(self._load())

    @threadsafe_method
    async def len(self):
        return len(self.storage.__dict__)

    @threadsafe_method
    async def setitem(self, key: Any, item: Context):
        key = str(key)
        self.storage.__dict__.__setitem__(key, item)
        await self._save()

    @threadsafe_method
    async def getitem(self, key: Any) -> Context:
        key = str(key)
        await self._load()
        value = self.storage.__dict__.__getitem__(key)
        return Context.cast(value)

    @threadsafe_method
    async def delitem(self, key: str) -> None:
        key = str(key)
        self.storage.__dict__.__delitem__(key)
        await self._save()

    @threadsafe_method
    async def contains(self, key: str) -> bool:
        key = str(key)
        await self._load()
        return self.storage.__dict__.__contains__(key)

    @threadsafe_method
    async def clear_async(self) -> None:
        self.storage.__dict__.clear()
        await self._save()

    async def _save(self) -> None:
        async with aiofiles.open(self.path, "w+", encoding="utf-8") as file_stream:
            await file_stream.write(self.storage.json())

    async def _load(self) -> None:
        if not await aiofiles.os.path.isfile(self.path) or (await aiofiles.os.stat(self.path)).st_size == 0:
            self.storage = SerializeableStorage()
            await self._save()
        else:
            async with aiofiles.open(self.path, "r", encoding="utf-8") as file_stream:
                self.storage = SerializeableStorage.parse_raw(await file_stream.read())
