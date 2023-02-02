"""
JSON
----
Provides the json-based version of the :py:class:`.DBContextStorage`.
"""
import os

from pydantic import BaseModel, Extra, root_validator

from .database import DBContextStorage, threadsafe_method
from dff.script import Context


class SerializeableStorage(BaseModel, extra=Extra.allow):
    @root_validator
    def validate_any(cls, vals):
        for key, value in vals.items():
            vals[key] = Context.cast(value)
        return vals


class JSONContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `json` as the storage format.

    :param path: Target file URI. Example: `json://file.json`.
    :type path: str
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)

        self._load()

    def get(self, key: str, default=None):
        key = str(key)
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    @threadsafe_method
    def __len__(self):
        return len(self.storage.__dict__)

    @threadsafe_method
    def __setitem__(self, key: str, item: Context) -> None:
        key = str(key)
        self.storage.__dict__.__setitem__(key, item)
        self._save()

    @threadsafe_method
    def __getitem__(self, key: str) -> Context:
        key = str(key)
        self._load()
        value = self.storage.__dict__.__getitem__(key)
        return Context.cast(value)

    @threadsafe_method
    def __delitem__(self, key: str) -> None:
        key = str(key)
        self.storage.__dict__.__delitem__(key)
        self._save()

    @threadsafe_method
    def __contains__(self, key: str) -> bool:
        key = str(key)
        self._load()
        return self.storage.__dict__.__contains__(key)

    @threadsafe_method
    def clear(self) -> None:
        self.storage.__dict__.clear()
        self._save()

    def _save(self) -> None:
        with open(self.path, "w+", encoding="utf-8") as file_stream:
            file_stream.write(self.storage.json())

    def _load(self) -> None:
        if not os.path.isfile(self.path) or os.stat(self.path).st_size == 0:
            self.storage = SerializeableStorage()
            self._save()
        else:
            with open(self.path, "r", encoding="utf-8") as file_stream:
                self.storage = SerializeableStorage.parse_raw(file_stream.read())
