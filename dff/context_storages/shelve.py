"""
Shelve
------
The Shelve module provides a shelve-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a shelve format.
It allows the `DFF` to easily store and retrieve context data in a format that is efficient
for serialization and deserialization and can be easily used in python.

Shelve is a python library that allows to store and retrieve python objects.
It is efficient and fast, but it is not recommended to use it to transfer data across different languages
or platforms because it's not cross-language compatible.
It stores data in a dbm-style format in the file system, which is not as fast as the other serialization
libraries like pickle or JSON.
"""
import pickle
from shelve import DbfilenameShelf
from typing import Hashable, Union, List, Any, Dict
from uuid import UUID

from dff.script import Context
from .update_scheme import UpdateScheme, FieldRule, UpdateSchemeBuilder, ExtraFields

from .database import DBContextStorage, auto_stringify_hashable_key


class ShelveContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `shelve` as the driver.

    :param path: Target file URI. Example: `shelve://file.db`.
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        self.shelve_db = DbfilenameShelf(filename=self.path, protocol=pickle.HIGHEST_PROTOCOL)

    def set_update_scheme(self, scheme: Union[UpdateScheme, UpdateSchemeBuilder]):
        super().set_update_scheme(scheme)
        self.update_scheme.mark_db_not_persistent()
        self.update_scheme.fields[ExtraFields.IDENTITY_FIELD].update(write=FieldRule.UPDATE)

    @auto_stringify_hashable_key()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        context, hashes = await self.update_scheme.process_fields_read(self._read_fields, self._read_value, self._read_seq, key)
        self.hash_storage[key] = hashes
        return context

    @auto_stringify_hashable_key()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        value_hash = self.hash_storage.get(key, None)
        await self.update_scheme.process_fields_write(value, value_hash, self._read_fields, self._write_anything, self._write_anything, key)

    @auto_stringify_hashable_key()
    async def del_item_async(self, key: Union[Hashable, str]):
        container = self.shelve_db.get(key, list())
        container.append(None)
        self.shelve_db[key] = container

    @auto_stringify_hashable_key()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        if key in self.shelve_db:
            container = self.shelve_db.get(key, list())
            if len(container) != 0:
                return container[-1] is not None
        return False

    async def len_async(self) -> int:
        return len(self.shelve_db)

    async def clear_async(self):
        self.shelve_db.clear()

    async def _read_fields(self, field_name: str, _: str, ext_id: Union[UUID, int, str]):
        container = self.shelve_db.get(ext_id, list())
        return list(container[-1].dict().get(field_name, dict()).keys()) if len(container) > 0 else list()

    async def _read_seq(self, field_name: str, outlook: List[Hashable], _: str, ext_id: Union[UUID, int, str]) -> Dict[Hashable, Any]:
        if ext_id not in self.shelve_db or self.shelve_db[ext_id][-1] is None:
            raise KeyError(f"Key {ext_id} not in storage!")
        container = self.shelve_db[ext_id]
        return {item: container[-1].dict().get(field_name, dict()).get(item, None) for item in outlook} if len(container) > 0 else dict()

    async def _read_value(self, field_name: str, _: str, ext_id: Union[UUID, int, str]) -> Any:
        if ext_id not in self.shelve_db or self.shelve_db[ext_id][-1] is None:
            raise KeyError(f"Key {ext_id} not in storage!")
        container = self.shelve_db[ext_id]
        return container[-1].dict().get(field_name, None) if len(container) > 0 else None

    async def _write_anything(self, field_name: str, data: Any, _: str, ext_id: Union[UUID, int, str]):
        container = self.shelve_db.setdefault(ext_id, list())
        if len(container) > 0:
            container[-1] = Context.cast({**container[-1].dict(), field_name: data})
        else:
            container.append(Context.cast({field_name: data}))
        self.shelve_db[ext_id] = container
