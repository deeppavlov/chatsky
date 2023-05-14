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
from typing import Hashable, Union, List, Any, Dict, Tuple, Optional

from dff.script import Context
from .context_schema import ContextSchema, SchemaFieldWritePolicy

from .database import DBContextStorage, cast_key_to_string


class ShelveContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `shelve` as the driver.

    :param path: Target file URI. Example: `shelve://file.db`.
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        self.shelve_db = DbfilenameShelf(filename=self.path, protocol=pickle.HIGHEST_PROTOCOL)

    def set_context_schema(self, scheme: ContextSchema):
        super().set_context_schema(scheme)
        self.context_schema.id.on_write = SchemaFieldWritePolicy.UPDATE

    @cast_key_to_string()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        fields, int_id = await self._read_keys(key)
        if int_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.context_schema.read_context(fields, self._read_ctx, key, int_id)
        self.hash_storage[key] = hashes
        return context

    @cast_key_to_string()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        fields, _ = await self._read_keys(key)
        value_hash = self.hash_storage.get(key, None)
        await self.context_schema.write_context(value, value_hash, fields, self._write_ctx, key)

    @cast_key_to_string()
    async def del_item_async(self, key: Union[Hashable, str]):
        container = self.shelve_db.get(key, list())
        container.append(None)
        self.shelve_db[key] = container

    @cast_key_to_string()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        if key in self.shelve_db:
            container = self.shelve_db.get(key, list())
            if len(container) != 0:
                return container[-1] is not None
        return False

    async def len_async(self) -> int:
        return len(self.shelve_db)

    async def clear_async(self):
        for key in self.shelve_db.keys():
            await self.del_item_async(key)

    async def _read_keys(self, ext_id: str) -> Tuple[Dict[str, List[str]], Optional[str]]:
        nested_dict_keys = dict()
        container = self.shelve_db.get(ext_id, list())
        if len(container) == 0:
            return nested_dict_keys, None
        container_dict = container[-1].dict() if container[-1] is not None else dict()
        for field in [key for key, value in container_dict.items() if isinstance(value, dict)]:
            nested_dict_keys[field] = list(container_dict.get(field, dict()).keys())
        return nested_dict_keys, container_dict.get(self.context_schema.id.name, None)

    async def _read_ctx(self, subscript: Dict[str, Union[bool, Dict[Hashable, bool]]], _: str, ext_id: str) -> Dict:
        result_dict = dict()
        context = self.shelve_db[ext_id][-1].dict()
        non_empty_value_subset = [
            field for field, value in subscript.items() if isinstance(value, dict) and len(value) > 0
        ]
        for field in non_empty_value_subset:
            for key in [key for key, value in subscript[field].items() if value]:
                value = context.get(field, dict()).get(key, None)
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

    async def _write_ctx(self, data: Dict[str, Any], _: str, ext_id: str):
        container = self.shelve_db.setdefault(ext_id, list())
        if len(container) > 0:
            container[-1] = Context.cast({**container[-1].dict(), **data})
        else:
            container.append(Context.cast(data))
        self.shelve_db[ext_id] = container
