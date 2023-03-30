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
from typing import Hashable, Union, List, Any, Dict
from uuid import UUID

from .update_scheme import UpdateScheme, FieldRule, UpdateSchemeBuilder, AdditionalFields

try:
    import aiofiles
    import aiofiles.os

    pickle_available = True
except ImportError:
    pickle_available = False
    aiofiles = None

from .database import DBContextStorage, threadsafe_method, auto_stringify_hashable_key
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

    def set_update_scheme(self, scheme: Union[UpdateScheme, UpdateSchemeBuilder]):
        super().set_update_scheme(scheme)
        self.update_scheme.mark_db_not_persistent()
        self.update_scheme.fields[AdditionalFields.IDENTITY_FIELD].update(write=FieldRule.UPDATE)

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        await self._load()
        context, hashes = await self.update_scheme.process_fields_read(self._read_fields, self._read_value, self._read_seq, key)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        value_hash = self.hash_storage.get(key, None)
        await self.update_scheme.process_fields_write(value, value_hash, self._read_fields, self._write_anything, self._write_anything, key)
        await self._save()

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def del_item_async(self, key: Union[Hashable, str]):
        container = self.storage.get(key, list())
        container.append(None)
        self.storage[key] = container
        await self._save()

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        await self._load()
        if key in self.storage:
            container = self.storage.get(key, list())
            if len(container) != 0:
                return container[-1] is not None
        return False

    @threadsafe_method
    async def len_async(self) -> int:
        return len(self.storage)

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

    async def _read_fields(self, field_name: str, _: str, ext_id: Union[UUID, int, str]):
        container = self.storage.get(ext_id, list())
        return list(container[-1].dict().get(field_name, dict()).keys()) if len(container) > 0 else list()

    async def _read_seq(self, field_name: str, outlook: List[Hashable], _: str, ext_id: Union[UUID, int, str]) -> Dict[Hashable, Any]:
        if ext_id not in self.storage or self.storage[ext_id][-1] is None:
            raise KeyError(f"Key {ext_id} not in storage!")
        container = self.storage[ext_id]
        return {item: container[-1].dict().get(field_name, dict()).get(item, None) for item in outlook} if len(container) > 0 else dict()

    async def _read_value(self, field_name: str, _: str, ext_id: Union[UUID, int, str]) -> Any:
        if ext_id not in self.storage or self.storage[ext_id][-1] is None:
            raise KeyError(f"Key {ext_id} not in storage!")
        container = self.storage[ext_id]
        return container[-1].dict().get(field_name, None) if len(container) > 0 else None

    async def _write_anything(self, field_name: str, data: Any, _: str, ext_id: Union[UUID, int, str]):
        container = self.storage.setdefault(ext_id, list())
        if len(container) > 0:
            container[-1] = Context.cast({**container[-1].dict(), field_name: data})
        else:
            container.append(Context.cast({field_name: data}))
