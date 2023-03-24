"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows the `DFF` to easily
store and retrieve context data.
"""
import asyncio
from typing import Hashable, Union, List, Any, Dict
from uuid import UUID

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
            vals[key] = [None if value is None else Context.cast(value) for value in values]
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
    async def get_item_async(self, key: Hashable) -> Context:
        key = str(key)
        await self._load()
        container = self.storage.__dict__.get(key, list())
        if len(container) == 0 or container[-1] is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await default_update_scheme.process_fields_read(self._read_fields, self._read_value, self._read_seq, container[-1].id, key)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        key = str(key)
        value_hash = self.hash_storage.get(key, dict())
        await default_update_scheme.process_fields_write(value, value_hash, self._read_fields, self._write_anything, self._write_anything, value.id, key)
        self.storage.__dict__[key][-1].id = value.id
        await self._save()

    @threadsafe_method
    async def del_item_async(self, key: Hashable):
        key = str(key)
        container = self.storage.__dict__.get(key, list())
        container.append(None)
        self.storage.__dict__[key] = container
        await self._save()

    @threadsafe_method
    async def contains_async(self, key: Hashable) -> bool:
        key = str(key)
        await self._load()
        if key in self.storage.__dict__:
            container = self.storage.__dict__.get(key, list())
            if len(container) != 0:
                return container[-1] is not None
        return False

    @threadsafe_method
    async def len_async(self) -> int:
        return len(self.storage.__dict__)

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

    async def _read_fields(self, field_name: str, _: Union[UUID, int, str], ext_id: Union[UUID, int, str]):
        container = self.storage.__dict__.get(ext_id, list())
        result = list(container[-1].dict().get(field_name, dict()).keys()) if len(container) > 0 else list()
        return result

    async def _read_seq(self, field_name: str, outlook: List[int], _: Union[UUID, int, str], ext_id: Union[UUID, int, str]) -> Dict[Hashable, Any]:
        container = self.storage.__dict__.get(ext_id, list())
        result = {item: container[-1].dict().get(field_name, dict()).get(item, None) for item in outlook} if len(container) > 0 else dict()
        return result

    async def _read_value(self, field_name: str, _: Union[UUID, int, str], ext_id: Union[UUID, int, str]) -> Any:
        container = self.storage.__dict__.get(ext_id, list())
        return container[-1].dict().get(field_name, None) if len(container) > 0 else None

    async def _write_anything(self, field_name: str, data: Dict[Hashable, Any], _: Union[UUID, int, str], ext_id: Union[UUID, int, str]):
        container = self.storage.__dict__.setdefault(ext_id, list())
        if len(container) > 0:
            container[-1] = Context.cast({**container[-1].dict(), field_name: data})
        else:
            container.append(Context.cast({field_name: data}))
