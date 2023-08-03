"""
Mongo
-----
The Mongo module provides a MongoDB-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a MongoDB.
It allows the DFF to easily store and retrieve context data in a format that is highly scalable
and easy to work with.

MongoDB is a widely-used, open-source NoSQL database that is known for its scalability and performance.
It stores data in a format similar to JSON, making it easy to work with the data in a variety of programming languages
and environments. Additionally, MongoDB is highly scalable and can handle large amounts of data
and high levels of read and write traffic.
"""
from typing import Hashable, Dict, Any

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson.objectid import ObjectId

    mongo_available = True
except ImportError:
    mongo_available = False
    AsyncIOMotorClient = None
    ObjectId = Any

import json

from dff.script import Context

from .database import DBContextStorage, threadsafe_method
from .protocol import get_protocol_install_suggestion


class MongoContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `mongodb` as the database backend.

    :param path: Database URI. Example: `mongodb://user:password@host:port/dbname`.
    :param collection: Name of the collection to store the data in.
    """

    def __init__(self, path: str, collection: str = "context_collection"):
        DBContextStorage.__init__(self, path)
        if not mongo_available:
            install_suggestion = get_protocol_install_suggestion("mongodb")
            raise ImportError("`mongodb` package is missing.\n" + install_suggestion)
        self._mongo = AsyncIOMotorClient(self.full_path)
        db = self._mongo.get_default_database()
        self.collection = db[collection]

    @staticmethod
    def _adjust_key(key: Hashable) -> Dict[str, ObjectId]:
        """Convert a n-digit context id to a 24-digit mongo id"""
        new_key = hex(int.from_bytes(str.encode(str(key)), "big", signed=False))[3:]
        new_key = (new_key * (24 // len(new_key) + 1))[:24]
        assert len(new_key) == 24
        return {"_id": ObjectId(new_key)}

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        new_key = self._adjust_key(key)
        value = value if isinstance(value, Context) else Context.cast(value)
        document = json.loads(value.model_dump_json())

        document.update(new_key)
        await self.collection.replace_one(new_key, document, upsert=True)

    @threadsafe_method
    async def get_item_async(self, key: Hashable) -> Context:
        adjust_key = self._adjust_key(key)
        document = await self.collection.find_one(adjust_key)
        if document:
            document.pop("_id")
            ctx = Context.cast(document)
            return ctx
        raise KeyError

    @threadsafe_method
    async def del_item_async(self, key: Hashable):
        adjust_key = self._adjust_key(key)
        await self.collection.delete_one(adjust_key)

    @threadsafe_method
    async def contains_async(self, key: Hashable) -> bool:
        adjust_key = self._adjust_key(key)
        return bool(await self.collection.find_one(adjust_key))

    @threadsafe_method
    async def len_async(self) -> int:
        return await self.collection.estimated_document_count()

    @threadsafe_method
    async def clear_async(self):
        await self.collection.delete_many(dict())
