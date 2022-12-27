"""
pickle
---------------------------
Provides the pickle-based version of the :py:class:`.DBContextStorage`.
"""
import asyncio
import pickle
from typing import Any

import aiofiles
import aiofiles.os

from .database import DBContextStorage, threadsafe_method
from dff.script import Context


class PickleContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `pickle` as driver.

    Parameters
    -----------

    path: str
        Target file URI. Example: 'pickle://file.pkl'
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)

        asyncio.run(self._load())

    @threadsafe_method
    async def len(self):
        return len(self.dict)

    @threadsafe_method
    async def setitem(self, key: Any, item: Context):
        key = str(key)
        self.dict.__setitem__(key, item)
        await self._save()

    @threadsafe_method
    async def getitem(self, key: Any) -> Context:
        key = str(key)
        await self._load()
        return Context.cast(self.dict.__getitem__(key))

    @threadsafe_method
    async def delitem(self, key: str) -> None:
        self.dict.__delitem__(key)
        await self._save()

    @threadsafe_method
    async def contains(self, key: str) -> bool:
        key = str(key)
        await self._load()
        return self.dict.__contains__(key)

    @threadsafe_method
    async def clear_async(self) -> None:
        self.dict.clear()
        await self._save()

    async def _save(self) -> None:
        async with aiofiles.open(self.path, "wb+") as file:
            await file.write(pickle.dumps(self.dict))

    async def _load(self) -> None:
        if not await aiofiles.os.path.isfile(self.path) or (await aiofiles.os.stat(self.path)).st_size == 0:
            self.dict = dict()
            await self._save()
        else:
            async with aiofiles.open(self.path, "rb") as file:
                self.dict = pickle.loads(await file.read())
