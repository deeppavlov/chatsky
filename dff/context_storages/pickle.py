"""
Pickle
------
The Pickle module provides a pickle-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a pickle format.
It allows the `DFF` to easily store and retrieve context data in a format that is efficient
for serialization and deserialization and can be easily used in python.

Pickle is a python library that allows to serialize and deserialize python objects.
It is efficient and fast, but it is not recommended to use it to transfer data across
different languages or platforms because it's not cross-language compatible.
"""
import asyncio
import pickle
from typing import Hashable

from .update_scheme import default_update_scheme

try:
    import aiofiles
    import aiofiles.os

    pickle_available = True
except ImportError:
    pickle_available = False

from .database import DBContextStorage, threadsafe_method
from dff.script import Context


class PickleContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `pickle` as driver.

    :param path: Target file URI. Example: 'pickle://file.pkl'.
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        self.storage = dict()
        asyncio.run(self._load())

    @threadsafe_method
    async def len_async(self) -> int:
        return len(self.storage)

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        key = str(key)
        container = self.storage.get(key, list())
        initial = None if len(container) == 0 else container[-1]
        if initial is not None and initial.get("id", None) == value.id:
            container[-1] = await default_update_scheme.process_context_write(value, initial)
        else:
            container.append(await default_update_scheme.process_context_write(value, dict()))
        self.storage[key] = container
        await self._save()

    @threadsafe_method
    async def get_item_async(self, key: Hashable) -> Context:
        await self._load()
        container = self.storage.get(str(key), list())
        if len(container) == 0:
            raise KeyError(f"No entry for key {key}.")
        return await default_update_scheme.process_context_read(container[-1])

    @threadsafe_method
    async def del_item_async(self, key: Hashable):
        del self.storage[str(key)]
        await self._save()

    @threadsafe_method
    async def contains_async(self, key: Hashable) -> bool:
        await self._load()
        return str(key) in self.storage

    @threadsafe_method
    async def clear_async(self):
        self.storage.clear()
        await self._save()

    async def _save(self):
        async with aiofiles.open(self.path, "wb+") as file:
            await file.write(pickle.dumps(self.storage))

    async def _load(self):
        if not await aiofiles.os.path.isfile(self.path) or (await aiofiles.os.stat(self.path)).st_size == 0:
            self.storage = dict()
            await self._save()
        else:
            async with aiofiles.open(self.path, "rb") as file:
                self.storage = pickle.loads(await file.read())
