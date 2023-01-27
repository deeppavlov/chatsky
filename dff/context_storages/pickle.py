"""
Pickle
------
Provides the pickle-based version of the :py:class:`.DBContextStorage`.
"""
import asyncio
import pickle
from typing import Hashable

import aiofiles
import aiofiles.os

from .database import DBAbstractContextStorage, threadsafe_method
from dff.script import Context


class PickleContextStorage(DBAbstractContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `pickle` as driver.

    :param path: Target file URI. Example: 'pickle://file.pkl'.
    :type path: str
    """

    def __init__(self, path: str):
        DBAbstractContextStorage.__init__(self, path)
        asyncio.run(self._load())

    @threadsafe_method
    async def len_async(self) -> int:
        return len(self.dict)

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        self.dict.__setitem__(str(key), value)
        await self._save()

    @threadsafe_method
    async def get_item_async(self, key: Hashable) -> Context:
        await self._load()
        return Context.cast(self.dict.__getitem__(str(key)))

    @threadsafe_method
    async def del_item_async(self, key: Hashable):
        self.dict.__delitem__(str(key))
        await self._save()

    @threadsafe_method
    async def contains_async(self, key: Hashable) -> bool:
        await self._load()
        return self.dict.__contains__(str(key))

    @threadsafe_method
    async def clear_async(self):
        self.dict.clear()
        await self._save()

    async def _save(self):
        async with aiofiles.open(self.path, "wb+") as file:
            await file.write(pickle.dumps(self.dict))

    async def _load(self):
        if not await aiofiles.os.path.isfile(self.path) or (await aiofiles.os.stat(self.path)).st_size == 0:
            self.dict = dict()
            await self._save()
        else:
            async with aiofiles.open(self.path, "rb") as file:
                self.dict = pickle.loads(await file.read())
