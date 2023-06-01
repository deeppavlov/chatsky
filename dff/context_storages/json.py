"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows the DFF to easily
store and retrieve context data.
"""
import asyncio
from typing import Hashable, Union, List, Any, Dict, Optional

from pydantic import BaseModel, Extra

from .context_schema import ALL_ITEMS, ExtraFields

try:
    import aiofiles
    import aiofiles.os

    json_available = True
except ImportError:
    json_available = False
    aiofiles = None

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from dff.script import Context


class SerializableStorage(BaseModel, extra=Extra.allow):
    pass


class JSONContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `json` as the storage format.

    :param path: Target file URI. Example: `json://file.json`.
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
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
        self.storage.__dict__[primary_id][ExtraFields.active_ctx.value] = False
        await self._save()

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        await self._load()
        return await self._get_last_ctx(key) is not None

    @threadsafe_method
    async def len_async(self) -> int:
        await self._load()
        return len([v for v in self.storage.__dict__.values() if v[ExtraFields.active_ctx.value]])

    @threadsafe_method
    async def clear_async(self):
        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        for key in self.storage.__dict__.keys():
            self.storage.__dict__[key][ExtraFields.active_ctx.value] = False
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

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        for key, value in self.storage.__dict__.items():
            if value[ExtraFields.storage_key.value] == storage_key and value[ExtraFields.active_ctx.value]:
                return key
        return None

    async def _read_ctx(self, subscript: Dict[str, Union[bool, int, List[Hashable]]], primary_id: str) -> Dict:
        context = dict()
        for key, value in subscript.items():
            source = self.storage.__dict__[primary_id][key]
            if isinstance(value, bool) and value:
                context[key] = source
            elif isinstance(source, dict):
                if isinstance(value, int):
                    read_slice = sorted(source.keys())[value:]
                    context[key] = {k: v for k, v in source.items() if k in read_slice}
                elif isinstance(value, list):
                    context[key] = {k: v for k, v in source.items() if k in value}
                elif value == ALL_ITEMS:
                    context[key] = source
        return context

    async def _write_ctx_val(self, key: str, data: Union[Dict[str, Any], Any], enforce: bool, nested: bool, primary_id: str):
        destination = self.storage.__dict__.setdefault(primary_id, dict())
        if nested:
            nested_destination = destination.setdefault(key, dict())
            for data_key, data_value in data.items():
                if enforce or data_key not in nested_destination:
                    nested_destination[data_key] = data_value
        else:
            if enforce or key not in destination:
                destination[key] = data
