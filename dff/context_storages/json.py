"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows the DFF to easily
store and retrieve context data.
"""
import asyncio
from typing import Hashable, Union, List, Any, Dict, Tuple, Optional

from pydantic import BaseModel, Extra, root_validator

from .context_schema import ContextSchema, ExtraFields

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
    @root_validator
    def validate_any(cls, vals):
        for key, values in vals.items():
            vals[key] = [None if value is None else value for value in values]
        return vals


class JSONContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `json` as the storage format.

    :param path: Target file URI. Example: `json://file.json`.
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        asyncio.run(self._load())

    def set_context_schema(self, scheme: ContextSchema):
        super().set_context_schema(scheme)
        self.context_schema.set_all_writable_rules_to_update()

    @threadsafe_method
    @cast_key_to_string()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        await self._load()
        fields, primary_id = await self._read_keys(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.context_schema.read_context(fields, self._read_ctx, primary_id, key)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @cast_key_to_string()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        fields, primary_id = await self._read_keys(key)
        value_hash = self.hash_storage.get(key)
        await self.context_schema.write_context(value, value_hash, fields, self._write_ctx, primary_id, key)
        await self._save()

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: Union[Hashable, str]):
        self.hash_storage[key] = None
        if key not in self.storage.__dict__:
            raise KeyError(f"No entry for key {key}.")
        if len(self.storage.__dict__[key]) > 0:
            self.storage.__dict__[key][-1][self.context_schema.active_ctx.name] = False 
        await self._save()

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        await self._load()
        if key in self.storage.__dict__:
            container = self.storage.__dict__.get(key, list())
            if len(container) != 0:
                return container[-1][self.context_schema.active_ctx.name]
        return False

    @threadsafe_method
    async def len_async(self) -> int:
        values = self.storage.__dict__.values()
        return len([v for v in values if len(v) > 0 and v[-1][self.context_schema.active_ctx.name]])

    @threadsafe_method
    async def clear_async(self):
        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        for key in self.storage.__dict__.keys():
            await self.del_item_async(key)
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

    async def _read_keys(self, storage_key: str) -> Tuple[Dict[str, List[str]], Optional[str]]:
        nested_dict_keys = dict()
        container = self.storage.__dict__.get(storage_key, list())
        if len(container) == 0:
            return nested_dict_keys, None
        container_dict = container[-1] if container[-1][self.context_schema.active_ctx.name] else dict()
        field_names = [key for key, value in container_dict.items() if isinstance(value, dict)]
        for field in field_names:
            nested_dict_keys[field] = list(container_dict.get(field, dict()).keys())
        return nested_dict_keys, container_dict.get(self.context_schema.primary_id.name, None)

    async def _read_ctx(self, subscript: Dict[str, Union[bool, Dict[Hashable, bool]]], _: str, storage_key: str) -> Dict:
        result_dict = dict()
        context = self.storage.__dict__[storage_key][-1]
        non_empty_value_subset = [
            field for field, value in subscript.items() if isinstance(value, dict) and len(value) > 0
        ]
        for field in non_empty_value_subset:
            non_empty_key_set = [key for key, value in subscript[field].items() if value]
            for key in non_empty_key_set:
                value = context.get(field, dict()).get(key)
                if value is not None:
                    if field not in result_dict:
                        result_dict[field] = dict()
                    result_dict[field][key] = value
        true_value_subset = [field for field, value in subscript.items() if isinstance(value, bool) and value]
        for field in true_value_subset:
            value = context.get(field, None)
            if value is not None:
                result_dict[field] = value
        return result_dict

    async def _write_ctx(self, data: Dict[str, Any], update: bool, _: str, storage_key: str):
        container = self.storage.__dict__.setdefault(storage_key, list())
        if update:
            container[-1] = {**container[-1], **data}
        else:
            container.append(data)
