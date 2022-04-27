"""
json_connector
---------------------------
Provides the json-based version of the :py:class:`~df_db.connector.db_connector.DBConnector`.
"""
import json
import os

from .db_connector import DBConnector, threadsafe_method
from df_engine.core.context import Context


class JSONConnector(dict, DBConnector):
    """
    Implements :py:class:`~df_db.connector.db_connector.DBConnector` with `json` as the storage format.

    Parameters
    -----------

    path: str
        Target file URI. Example: 'json://file.json'
    """

    def __new__(cls, path: str):
        obj = dict.__new__(cls)
        return obj

    def __init__(self, path: str):
        DBConnector.__init__(self, path)

        if not os.path.isfile(self.path):
            open(self.path, "a").close()

    def get(self, key: str, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    @threadsafe_method
    def __getitem__(self, key: str) -> Context:
        self._load()
        value = dict.__getitem__(self, key)
        return Context.cast(value)

    @threadsafe_method
    def __setitem__(self, key: str, value: Context) -> None:

        value_dict = value.dict() if isinstance(value, Context) else value

        if not isinstance(value_dict, dict):
            raise TypeError(f"The saved value should be a dict or a dict-serializeable item, not {type(value_dict)}")

        dict.__setitem__(self, key, value_dict)
        self._save()

    @threadsafe_method
    def __delitem__(self, key: str):
        dict.__delitem__(self, key)
        self._save()

    @threadsafe_method
    def clear(self):
        dict.clear(self)

    def _save(self) -> None:
        with open(self.path, "w+", encoding="utf-8") as file_stream:
            json.dump(self, file_stream, ensure_ascii=False)

    def _load(self) -> None:
        if os.stat(self.path).st_size == 0:
            return
        with open(self.path, "r", encoding="utf-8") as file_stream:
            saved_values = json.load(file_stream)
        for key, value in saved_values.items():
            if key not in self:
                self[key] = value
