"""
Shelve
------
Provides the shelve-based version of the :py:class:`.DBContextStorage`.
"""
import pickle
from shelve import DbfilenameShelf

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

    def get(self, key: str, default=None):
        return self.shelve_db.get(str(key), default)

    def __setitem__(self, key: str, item: Context) -> None:
        return self.shelve_db.__setitem__(str(key), item)

    def __getitem__(self, key: str) -> Context:
        return self.shelve_db.__getitem__(str(key))

    def __delitem__(self, key: str) -> None:
        return self.shelve_db.__delitem__(str(key))

    def __contains__(self, key: str) -> bool:
        return self.shelve_db.__contains__(str(key))

    def __len__(self) -> int:
        return self.shelve_db.__len__()

    def clear(self) -> None:
        return self.shelve_db.clear()
