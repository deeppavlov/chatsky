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
from typing import Hashable

from dff.script import Context

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
        return self.shelve_db[str(key)]

    async def set_item_async(self, key: Hashable, value: Context):
        self.shelve_db.__setitem__(str(key), value)

    async def del_item_async(self, key: Hashable):
        self.shelve_db.__delitem__(str(key))

    async def contains_async(self, key: Hashable) -> bool:
        return self.shelve_db.__contains__(str(key))

    async def len_async(self) -> int:
        return self.shelve_db.__len__()

    async def clear_async(self):
        self.shelve_db.clear()
