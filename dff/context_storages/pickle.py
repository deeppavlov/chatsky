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
from typing import Hashable, Union, List, Any, Dict, Tuple, Optional

from .update_scheme import UpdateScheme, FieldRule, UpdateSchemeBuilder, ExtraFields

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
        self.update_scheme.fields[ExtraFields.IDENTITY_FIELD].on_write = FieldRule.UPDATE

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        await self._load()
        fields, int_id = await self._read_keys(key)
        if int_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.update_scheme.read_context(fields, self._read_ctx, key, int_id)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        fields, _ = await self._read_keys(key)
        value_hash = self.hash_storage.get(key, None)
        await self.update_scheme.write_context(value, value_hash, fields, self._write_ctx, key)
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

    async def _read_keys(self, ext_id: str) -> Tuple[Dict[str, List[str]], Optional[str]]:
        key_dict = dict()
        container = self.storage.get(ext_id, list())
        if len(container) == 0:
            return key_dict, None
        container_dict = container[-1].dict() if container[-1] is not None else dict()
        for field in [key for key, value in container_dict.items() if isinstance(value, dict)]:
            key_dict[field] = list(container_dict.get(field, dict()).keys())
        return key_dict, container_dict.get(ExtraFields.IDENTITY_FIELD, None)

    async def _read_ctx(self, outlook: Dict[str, Union[bool, Dict[Hashable, bool]]], _: str, ext_id: str) -> Dict:
        result_dict = dict()
        context = self.storage[ext_id][-1].dict()
        for field in [field for field, value in outlook.items() if isinstance(value, dict) and len(value) > 0]:
            for key in [key for key, value in outlook[field].items() if value]:
                value = context.get(field, dict()).get(key, None)
                if value is not None:
                    if field not in result_dict:
                        result_dict[field] = dict()
                    result_dict[field][key] = value
        for field in [field for field, value in outlook.items() if isinstance(value, bool) and value]:
            value = context.get(field, None)
            if value is not None:
                result_dict[field] = value
        return result_dict

    async def _write_ctx(self, data: Dict[str, Any], _: str, ext_id: str):
        container = self.storage.setdefault(ext_id, list())
        if len(container) > 0:
            container[-1] = Context.cast({**container[-1].dict(), **data})
        else:
            container.append(Context.cast(data))
