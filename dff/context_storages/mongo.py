"""
mongo
---------------------------
Provides the mongo-based version of the :py:class:`.DBContextStorage`.
"""
from typing import Any

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson.objectid import ObjectId

    mongo_available = True
except ImportError:
    mongo_available = False

import json

from dff.script import Context

from .database import DBContextStorage, threadsafe_method
from .protocol import get_protocol_install_suggestion


class MongoContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `mongodb` as the database backend.

    Parameters
    -----------

    path: str
        Database URI. Example: 'mongodb://user:password@host:port/dbname'
    collection: str
        Name of the collection to store the data in.
    """

    def __init__(self, path: str, collection: str = "context_collection"):
        super(MongoContextStorage, self).__init__(path)
        if not mongo_available:
            install_suggestion = get_protocol_install_suggestion("mongodb")
            raise ImportError("`mongodb` package is missing.\n" + install_suggestion)
        self._mongo = AsyncIOMotorClient(self.full_path)
        db = self._mongo.get_default_database()
        self.collection = db[collection]

    @staticmethod
    def _adjust_key(key: str):
        """Convert a n-digit context id to a 24-digit mongo id"""
        new_key = hex(int.from_bytes(str.encode(str(key)), "big", signed=False))[3:]
        new_key = (new_key * (24 // len(new_key) + 1))[:24]
        assert len(new_key) == 24
        return {"_id": ObjectId(new_key)}

    @threadsafe_method
    async def setitem(self, key: Any, value: Context) -> None:
        new_key = self._adjust_key(key)
        value = value if isinstance(value, Context) else Context.cast(value)
        document = json.loads(value.json())

        document.update(new_key)
        await self.collection.replace_one(new_key, document, upsert=True)

    @threadsafe_method
    async def getitem(self, key: Any) -> Context:
        adjust_key = self._adjust_key(key)
        document = await self.collection.find_one(adjust_key)
        if document:
            document.pop("_id")
            ctx = Context.cast(document)
            return ctx
        raise KeyError

    @threadsafe_method
    async def delitem(self, key: str) -> None:
        adjust_key = self._adjust_key(key)
        await self.collection.delete_one(adjust_key)

    @threadsafe_method
    async def contains(self, key: str) -> bool:
        adjust_key = self._adjust_key(key)
        return bool(await self.collection.find_one(adjust_key))

    @threadsafe_method
    async def len(self) -> int:
        return await self.collection.estimated_document_count()

    @threadsafe_method
    async def clear_async(self) -> None:
        await self.collection.delete_many(dict())
