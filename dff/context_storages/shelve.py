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
from typing import Hashable

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
        if len(container) == 0:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await default_update_scheme.process_context_read(container[-1])
        self.hash_storage[key] = hashes
        return context

    async def set_item_async(self, key: Hashable, value: Context):
        key = str(key)
        container = self.shelve_db.get(key, list())
        initial = None if len(container) == 0 else container[-1]
        if initial is not None and initial.get("id", None) == value.id:
            value_hash = self.hash_storage.get(key, dict())
            container[-1] = await default_update_scheme.process_context_write(value, value_hash, initial)
        else:
            container.append(await default_update_scheme.process_context_write(value, dict(), dict()))
        self.shelve_db[key] = container

    async def del_item_async(self, key: Hashable):
        del self.shelve_db[str(key)]

    async def contains_async(self, key: Hashable) -> bool:
        return str(key) in self.shelve_db

    async def len_async(self) -> int:
        return len(self.shelve_db)

    async def clear_async(self):
        self.shelve_db.clear()
