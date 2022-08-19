"""
pickle_connector
---------------------------
Provides the pickle-based version of the :py:class:`~df_db_connector.db_connector.DBConnector`.
"""
import pickle
import os

from .db_connector import DBConnector, threadsafe_method
from df_engine.core.context import Context


class PickleConnector(DBConnector):
    """
    Implements :py:class:`~df_db_connector.db_connector.DBConnector` with `pickle` as driver.

    Parameters
    -----------

    path: str
        Target file URI. Example: 'pickle://file.pkl'
    """

    def __init__(self, path: str):
        DBConnector.__init__(self, path)

        self._load()

    @threadsafe_method
    def __len__(self):
        return len(self.dict)

    @threadsafe_method
    def __setitem__(self, key: str, item: Context) -> None:
        self.dict.__setitem__(key, item)
        self._save()

    @threadsafe_method
    def __getitem__(self, key: str) -> Context:
        self._load()
        return self.dict.__getitem__(key)

    @threadsafe_method
    def __delitem__(self, key: str) -> None:
        self.dict.__delitem__(key)
        self._save()

    @threadsafe_method
    def __contains__(self, key: str) -> bool:
        self._load()
        return self.dict.__contains__(key)

    @threadsafe_method
    def clear(self) -> None:
        self.dict.clear()
        self._save()

    def _save(self) -> None:
        with open(self.path, "wb+") as file:
            pickle.dump(self.dict, file)

    def _load(self) -> None:
        if not os.path.isfile(self.path) or os.stat(self.path).st_size == 0:
            self.dict = dict()
            open(self.path, "a").close()
        else:
            with open(self.path, "rb") as file:
                self.dict = pickle.load(file)
