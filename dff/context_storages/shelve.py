"""
Shelve
------
Provides the shelve-based version of the :py:class:`.DBContextStorage`.
"""
import pickle
from shelve import DbfilenameShelf
from typing import Any

from dff.script import Context

from .database import DBContextStorage


class ShelveContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `shelve` as the driver.

    :param path: Target file URI. Example: `shelve://file.db`.
    :type path: str
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        self.shelve_db = DbfilenameShelf(filename=self.path, protocol=pickle.HIGHEST_PROTOCOL)

    def __del__(self):
        self.shelve_db.close()
        del self

    async def delete(self):
        self.__del__()

    async def get_async(self, key: Any, default=None):
        return self.shelve_db.get(str(key), default)

    async def setitem(self, key: Any, item: Context):
        return self.shelve_db.__setitem__(str(key), item)

    async def getitem(self, key: Any) -> Context:
        return self.shelve_db.__getitem__(str(key))

    async def delitem(self, key: str) -> None:
        return self.shelve_db.__delitem__(str(key))

    async def contains(self, key: str) -> bool:
        return self.shelve_db.__contains__(str(key))

    async def len(self) -> int:
        return self.shelve_db.__len__()

    async def clear_async(self) -> None:
        return self.shelve_db.clear()
