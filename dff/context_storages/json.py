"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows the `DFF` to easily
store and retrieve context data.
"""
import asyncio
from typing import Hashable

from pydantic import BaseModel, Extra, root_validator

from .update_scheme import default_update_scheme

try:
    import aiofiles
    import aiofiles.os

    json_available = True
except ImportError:
    json_available = False

from .database import DBContextStorage, threadsafe_method
from dff.script import Context


class SerializableStorage(BaseModel, extra=Extra.allow):
    @root_validator
    def validate_any(cls, vals):
        for key, values in vals.items():
            vals[key] = [Context.cast(value) for value in values]
        return vals


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
        return len(self.storage.__dict__)

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        key = str(key)
        container = self.storage.__dict__.get(key, list())
        initial = None if len(container) == 0 else container[-1]
        if initial is not None and initial.dict().get("id", None) == value.id:
            container[-1] = default_update_scheme.process_context_write(value, initial.dict())
        else:
            container.append(default_update_scheme.process_context_write(value, dict()))
        self.storage.__dict__[key] = container
        await self._save()

    @threadsafe_method
    async def get_item_async(self, key: Hashable) -> Context:
        await self._load()
        container = self.storage.__dict__.get(str(key), list())
        if len(container) == 0:
            raise KeyError(f"No entry for key {key}.")
        return default_update_scheme.process_context_read(container[-1].dict())

    @threadsafe_method
    async def del_item_async(self, key: Hashable):
        self.storage.__dict__.__delitem__(str(key))
        await self._save()

    @threadsafe_method
    async def contains_async(self, key: Hashable) -> bool:
        await self._load()
        return str(key) in self.storage.__dict__

    @threadsafe_method
    async def clear_async(self):
        self.storage.__dict__.clear()
        await self._save()

    async def _save(self):
        async with aiofiles.open(self.path, "w+", encoding="utf-8") as file_stream:
            await file_stream.write(self.storage.json())

    async def _load(self):
        if not await aiofiles.os.path.isfile(self.path) or (await aiofiles.os.stat(self.path)).st_size == 0:
            self.storage = SerializableStorage()
            await self._save()
        else:
            async with aiofiles.open(self.path, "r", encoding="utf-8") as file_stream:
                self.storage = SerializableStorage.parse_raw(await file_stream.read())
