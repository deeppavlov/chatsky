"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows the DFF to easily
store and retrieve context data.
"""
import asyncio
from typing import Hashable

try:
    import aiofiles
    import aiofiles.os

    json_available = True
except ImportError:
    json_available = False

from pydantic import BaseModel, model_validator

from .database import DBContextStorage, threadsafe_method
from dff.script import Context


class SerializableStorage(BaseModel, extra="allow"):
    @model_validator(mode="before")
    @classmethod
    def validate_any(cls, vals):
        for key, value in vals.items():
            vals[key] = Context.cast(value)
        return vals


class JSONContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `json` as the storage format.

    :param path: Target file URI. Example: `json://file.json`.
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        asyncio.run(self._load())

    @threadsafe_method
    async def len_async(self) -> int:
        return len(self.storage.model_extra)

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        self.storage.model_extra.__setitem__(str(key), value)
        await self._save()

    @threadsafe_method
    async def get_item_async(self, key: Hashable) -> Context:
        await self._load()
        return Context.cast(self.storage.model_extra.__getitem__(str(key)))

    @threadsafe_method
    async def del_item_async(self, key: Hashable):
        self.storage.model_extra.__delitem__(str(key))
        await self._save()

    @threadsafe_method
    async def contains_async(self, key: Hashable) -> bool:
        await self._load()
        return self.storage.model_extra.__contains__(str(key))

    @threadsafe_method
    async def clear_async(self):
        self.storage.model_extra.clear()
        await self._save()

    async def _save(self):
        async with aiofiles.open(self.path, "w+", encoding="utf-8") as file_stream:
            await file_stream.write(self.storage.model_dump_json())

    async def _load(self):
        if not await aiofiles.os.path.isfile(self.path) or (await aiofiles.os.stat(self.path)).st_size == 0:
            self.storage = SerializableStorage()
            await self._save()
        else:
            async with aiofiles.open(self.path, "r", encoding="utf-8") as file_stream:
                self.storage = SerializableStorage.model_validate_json(await file_stream.read())
