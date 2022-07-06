"""
json_connector
---------------------------
Provides the json-based version of the :py:class:`~df_db.connector.db_connector.DBConnector`.
"""
import json
import os

from .db_connector import DBConnector, threadsafe_method
from df_engine.core.context import Context


class JSONConnector(DBConnector):
    """
    Implements :py:class:`~df_db.connector.db_connector.DBConnector` with `json` as the storage format.

    Parameters
    -----------

    path: str
        Target file URI. Example: 'json://file.json'
    """

    def __init__(self, path: str):
        DBConnector.__init__(self, path)

        self._load()

    def get(self, key: str, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    @threadsafe_method
    def __len__(self):
        return len(self.dict)

    @threadsafe_method
    def __setitem__(self, key: str, item: Context) -> None:
        value_dict = item.dict() if isinstance(item, Context) else item

        if not isinstance(value_dict, dict):
            raise TypeError(f"The saved value should be a dict or a dict-serializeable item, not {type(value_dict)}")

        self.dict.__setitem__(key, value_dict)
        self._save()

    @threadsafe_method
    def __getitem__(self, key: str) -> Context:
        self._load()
        value = self.dict.__getitem__(key)
        return Context.cast(value)

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
        with open(self.path, "w+", encoding="utf-8") as file_stream:
            json.dump(self.dict, file_stream, ensure_ascii=False)

    def _load(self) -> None:
        if not os.path.isfile(self.path) or os.stat(self.path).st_size == 0:
            self.dict = dict()
            self._save()
        else:
            with open(self.path, "r", encoding="utf-8") as file_stream:
                self.dict = json.load(file_stream)
