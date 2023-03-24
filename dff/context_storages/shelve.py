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
from .update_scheme import default_update_scheme

from .database import DBContextStorage


class ShelveContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `shelve` as the driver.

    :param path: Target file URI. Example: `shelve://file.db`.
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        self.shelve_db = DbfilenameShelf(filename=self.path, protocol=pickle.HIGHEST_PROTOCOL)

    async def get_item_async(self, key: Hashable) -> Context:
        key = str(key)
        container = self.shelve_db.get(key, list())
        if len(container) == 0 or container[-1] is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await default_update_scheme.process_fields_read(self._read_fields, self._read_value, self._read_seq, container[-1].id, key)
        self.hash_storage[key] = hashes
        return context

    async def set_item_async(self, key: Hashable, value: Context):
        key = str(key)
        value_hash = self.hash_storage.get(key, dict())
        await default_update_scheme.process_fields_write(value, value_hash, self._read_fields, self._write_anything, self._write_anything, value.id, key)
        self.shelve_db[key] = self.shelve_db[key][:-1] + [Context.cast(dict(self.shelve_db[key][-1].dict(), id=value.id))]

    async def del_item_async(self, key: Hashable):
        key = str(key)
        container = self.shelve_db.get(key, list())
        container.append(None)
        self.shelve_db[key] = container

    async def contains_async(self, key: Hashable) -> bool:
        key = str(key)
        if key in self.shelve_db:
            container = self.shelve_db.get(key, list())
            if len(container) != 0:
                return container[-1] is not None
        return False

    async def len_async(self) -> int:
        return len(self.shelve_db)

    async def clear_async(self):
        self.shelve_db.clear()

    async def _read_fields(self, field_name: str, _: Union[UUID, int, str], ext_id: Union[UUID, int, str]):
        container = self.shelve_db.get(ext_id, list())
        result = list(container[-1].dict().get(field_name, dict()).keys()) if len(container) > 0 else list()
        return result

    async def _read_seq(self, field_name: str, outlook: List[int], _: Union[UUID, int, str], ext_id: Union[UUID, int, str]) -> Dict[Hashable, Any]:
        container = self.shelve_db.get(ext_id, list())
        result = {item: container[-1].dict().get(field_name, dict()).get(item, None) for item in outlook} if len(container) > 0 else dict()
        return result

    async def _read_value(self, field_name: str, _: Union[UUID, int, str], ext_id: Union[UUID, int, str]) -> Any:
        container = self.shelve_db.get(ext_id, list())
        return container[-1].dict().get(field_name, None) if len(container) > 0 else None

    async def _write_anything(self, field_name: str, data: Dict[Hashable, Any], _: Union[UUID, int, str], ext_id: Union[UUID, int, str]):
        container = self.shelve_db.setdefault(ext_id, list())
        if len(container) > 0:
            container[-1] = Context.cast({**container[-1].dict(), field_name: data})
        else:
            container.append(Context.cast({field_name: data}))
        self.shelve_db[ext_id] = container
