"""
Pickle
------
The Pickle module provides a pickle-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a pickle format.
It allows the `DFF` to easily store and retrieve context data in a format that is efficient
for serialization and deserialization and can be easily used in python.

Pickle is a python library that allows to serialize and deserialize python objects.
It is efficient and fast, but it is not recommended to use it to transfer data across
different languages or platforms because it's not cross-language compatible.
"""
import pickle
import os

from .database import DBContextStorage, threadsafe_method
from dff.script import Context


class PickleContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `pickle` as driver.

    :param path: Target file URI. Example: 'pickle://file.pkl'.
    :type path: str
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)

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
