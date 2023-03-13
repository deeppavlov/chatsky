"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows the `DFF` to easily
store and retrieve context data.
"""
import asyncio
import json
from typing import Hashable

from .update_scheme import default_update_scheme

try:
    import aiofiles
    import aiofiles.os

    json_available = True
except ImportError:
    json_available = False

from .database import DBContextStorage, threadsafe_method
from dff.script import Context


class JSONContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `json` as the storage format.

    :param path: Target file URI. Example: `json://file.json`.
    :type path: str
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        asyncio.run(self._load())

    @threadsafe_method
    async def len_async(self) -> int:
        return len(self.storage)

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        key = str(key)
        initial = self.storage.get(key, dict())
        ctx_dict = default_update_scheme.process_context_write(value, initial)
        self.storage[key] = ctx_dict
        await self._save()

    @threadsafe_method
    async def get_item_async(self, key: Hashable) -> Context:
        key = str(key)
        await self._load()
        ctx_dict, _ = default_update_scheme.process_context_read(self.storage[key])
        return Context.cast(ctx_dict)

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
        async with aiofiles.open(self.path, "w+", encoding="utf-8") as file_stream:
            await file_stream.write(json.dumps(self.storage))

    async def _load(self):
        if not await aiofiles.os.path.isfile(self.path) or (await aiofiles.os.stat(self.path)).st_size == 0:
            self.storage = dict()
            await self._save()
        else:
            async with aiofiles.open(self.path, "r", encoding="utf-8") as file_stream:
                self.storage = json.loads(await file_stream.read())
