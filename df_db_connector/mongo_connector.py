"""
mongo_connector
---------------------------
Provides the mongo-based version of the :py:class:`~df_db.connector.db_connector.DBConnector`.
"""
import json
from functools import wraps
from typing import Callable

try:
    from bson.objectid import ObjectId
    from pymongo import MongoClient

    mongo_available = True
except ImportError:
    mongo_available = False

from .db_connector import DBConnector, threadsafe_method
from df_engine.core.context import Context


class MongoConnector(DBConnector):
    """
    Implements :py:class:`~df_db.connector.db_connector.DBConnector` with `mongodb` as the database backend.

    Parameters
    -----------

    path: str
        Database URI. Example: 'mongodb://user:password@host:port/dbname'
    collection: str
        Name of the collection to store the data in.
    """

    def __init__(self, path: str, collection: str = "context_collection"):
        super(MongoConnector, self).__init__(path)
        if not mongo_available:
            raise ImportError("`pymongo` package is missing.")
        self._mongo = MongoClient(self.full_path)
        db = self._mongo.get_default_database()
        self.collection = db[collection]

    @staticmethod
    def _adjust_key(key: str):
        """Convert a 9-digit telegram user id to a 24-digit mongo id"""
        new_key = key + "0" * (24 - len(key))
        assert len(new_key) == 24
        return {"_id": ObjectId(new_key)}

    @threadsafe_method
    def __setitem__(self, key: str, value: Context) -> None:
        new_key = self._adjust_key(key)
        value_dict = value.dict() if isinstance(value, Context) else value

        if not isinstance(value_dict, dict):
            raise TypeError(f"The saved value should be a dict or a dict-serializeable item, not {type(value_dict)}")

        value_dict.update(new_key)
        self.collection.replace_one(new_key, value_dict, upsert=True)

    @threadsafe_method
    def __getitem__(self, key: str) -> Context:
        key = self._adjust_key(key)
        value = self.collection.find_one(key)
        if value:
            value.pop("_id")
            return Context.cast(value)
        raise KeyError

    @threadsafe_method
    def __delitem__(self, key: str) -> None:
        key = self._adjust_key(key)
        self.collection.delete_one(key)

    @threadsafe_method
    def __contains__(self, key: str) -> bool:
        key = self._adjust_key(key)
        return bool(self.collection.find_one(key))

    @threadsafe_method
    def __len__(self) -> int:
        return self.collection.estimated_document_count()

    @threadsafe_method
    def clear(self) -> None:
        self.collection.delete_many(dict())
