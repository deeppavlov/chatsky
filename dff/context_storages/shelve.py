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
        ctx_dict, _ = default_update_scheme.process_context_read(self.shelve_db[key])
        return Context.cast(ctx_dict)

    async def set_item_async(self, key: Hashable, value: Context):
        key = str(key)
        initial = self.shelve_db.get(key, dict())
        initial = initial if initial.get("id", None) == value.id else dict()
        ctx_dict = default_update_scheme.process_context_write(value, initial)
        self.shelve_db[key] = ctx_dict

    async def del_item_async(self, key: Hashable):
        del self.shelve_db[str(key)]

    async def contains_async(self, key: Hashable) -> bool:
        return str(key) in self.shelve_db

    async def len_async(self) -> int:
        return len(self.shelve_db)

    async def clear_async(self):
        self.shelve_db.clear()
