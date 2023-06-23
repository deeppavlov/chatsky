"""
Pickle
------
The Pickle module provides a pickle-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a pickle format.
It allows the DFF to easily store and retrieve context data in a format that is efficient
for serialization and deserialization and can be easily used in python.

Pickle is a python library that allows to serialize and deserialize python objects.
It is efficient and fast, but it is not recommended to use it to transfer data across
different languages or platforms because it's not cross-language compatible.
"""
import asyncio
import pickle
from typing import Hashable, Union, List, Dict, Optional

from .context_schema import ALL_ITEMS, ExtraFields

try:
    import aiofiles
    import aiofiles.os

    pickle_available = True
except ImportError:
    pickle_available = False
    aiofiles = None

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
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
    @cast_key_to_string()
    async def get_item_async(self, key: str) -> Context:
        await self._load()
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.context_schema.read_context(self._read_ctx, key, primary_id)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @cast_key_to_string()
    async def set_item_async(self, key: str, value: Context):
        primary_id = await self._get_last_ctx(key)
        value_hash = self.hash_storage.get(key)
        await self.context_schema.write_context(value, value_hash, self._write_ctx_val, key, primary_id)
        await self._save()

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: str):
        self.hash_storage[key] = None
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        self.storage[primary_id][ExtraFields.active_ctx.value] = False
        await self._save()

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        await self._load()
        return await self._get_last_ctx(key) is not None

    @threadsafe_method
    async def len_async(self) -> int:
        await self._load()
        return len([v for v in self.storage.values() if v[ExtraFields.active_ctx.value]])

    @threadsafe_method
    async def clear_async(self):
        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        for key in self.storage.keys():
            self.storage[key][ExtraFields.active_ctx.value] = False
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

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        for key, value in self.storage.items():
            if value[ExtraFields.storage_key.value] == storage_key and value[ExtraFields.active_ctx.value]:
                return key
        return None

    async def _read_ctx(self, subscript: Dict[str, Union[bool, int, List[Hashable]]], primary_id: str) -> Dict:
        context = dict()
        for key, value in subscript.items():
            source = self.storage[primary_id][key]
            if isinstance(value, bool) and value:
                context[key] = source
            else:
                if isinstance(value, int):
                    read_slice = sorted(source.keys())[value:]
                    context[key] = {k: v for k, v in source.items() if k in read_slice}
                elif isinstance(value, list):
                    context[key] = {k: v for k, v in source.items() if k in value}
                elif value == ALL_ITEMS:
                    context[key] = source
        return context

    async def _write_ctx_val(self, field: Optional[str], payload: Dict, nested: bool, primary_id: str):
        destination = self.storage.setdefault(primary_id, dict())
        if nested:
            data, enforce = payload
            nested_destination = destination.setdefault(field, dict())
            for key, value in data.items():
                if enforce or key not in nested_destination:
                    nested_destination[key] = value
        else:
            for key, (data, enforce) in payload.items():
                if enforce or key not in destination:
                    destination[key] = data
