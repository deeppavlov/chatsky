"""
Shelve
------
The Shelve module provides a shelve-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a shelve format.
It allows the DFF to easily store and retrieve context data in a format that is efficient
for serialization and deserialization and can be easily used in python.

Shelve is a python library that allows to store and retrieve python objects.
It is efficient and fast, but it is not recommended to use it to transfer data across different languages
or platforms because it's not cross-language compatible.
It stores data in a dbm-style format in the file system, which is not as fast as the other serialization
libraries like pickle or JSON.
"""
import pickle
from shelve import DbfilenameShelf
from typing import Hashable, Union, List, Any, Dict, Optional

from dff.script import Context
from .context_schema import ALL_ITEMS, ExtraFields

from .database import DBContextStorage, cast_key_to_string


class ShelveContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `shelve` as the driver.

    :param path: Target file URI. Example: `shelve://file.db`.
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        self.shelve_db = DbfilenameShelf(filename=self.path, writeback=True, protocol=pickle.HIGHEST_PROTOCOL)

    @cast_key_to_string()
    async def get_item_async(self, key: str) -> Context:
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.context_schema.read_context(self._read_ctx, key, primary_id)
        self.hash_storage[key] = hashes
        return context

    @cast_key_to_string()
    async def set_item_async(self, key: str, value: Context):
        primary_id = await self._get_last_ctx(key)
        value_hash = self.hash_storage.get(key)
        await self.context_schema.write_context(value, value_hash, self._write_ctx_val, key, primary_id)

    @cast_key_to_string()
    async def del_item_async(self, key: str):
        self.hash_storage[key] = None
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        self.shelve_db[primary_id][ExtraFields.active_ctx.value] = False

    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        return await self._get_last_ctx(key) is not None

    async def len_async(self) -> int:
        return len([v for v in self.shelve_db.values() if v[ExtraFields.active_ctx.value]])

    async def clear_async(self):
        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        for key in self.shelve_db.keys():
            self.shelve_db[key][ExtraFields.active_ctx.value] = False

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        for key, value in self.shelve_db.items():
            if value[ExtraFields.storage_key.value] == storage_key and value[ExtraFields.active_ctx.value]:
                return key
        return None

    async def _read_ctx(self, subscript: Dict[str, Union[bool, int, List[Hashable]]], primary_id: str) -> Dict:
        context = dict()
        for key, value in subscript.items():
            source = self.shelve_db[primary_id][key]
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
        destination = self.shelve_db.setdefault(primary_id, dict())
        if nested:
            nested_destination = destination.setdefault(key, dict())
            for data_key, data_value in data.items():
                if enforce or data_key not in nested_destination:
                    nested_destination[data_key] = data_value
        else:
            if enforce or key not in destination:
                destination[key] = data
