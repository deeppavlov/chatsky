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
import asyncio
import datetime
import pickle
from typing import Dict, Tuple, Optional, List, Any

try:
    from pymongo import ASCENDING, HASHED, UpdateOne
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_available = True
except ImportError:
    mongo_available = False
    AsyncIOMotorClient = None
    ObjectId = None

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from .protocol import get_protocol_install_suggestion
from .context_schema import ALL_ITEMS, ExtraFields


class MongoContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `mongodb` as the database backend.

    Context value fields are stored in `COLLECTION_PREFIX_contexts` collection as dictionaries.
    Extra field `_id` contains mongo-specific unique identifier.

    Context dictionary fields are stored in `COLLECTION_PREFIX_FIELD` collection as dictionaries.
    Extra field `_id` contains mongo-specific unique identifier.
    Extra fields starting with `__mongo_misc_key` contain additional information for statistics and should be ignored.
    Additional information includes primary identifier, creation and update date and time.

    :param path: Database URI. Example: `mongodb://user:password@host:port/dbname`.
    :param collection: Name of the collection to store the data in.
    """

    _CONTEXTS_TABLE = "contexts"
    _LOGS_TABLE = "logs"
    _KEY_COLUMN = "key"
    _VALUE_COLUMN = "value"
    _PACKED_COLUMN = "data"

    def __init__(self, path: str, collection_prefix: str = "dff_collection"):
        DBContextStorage.__init__(self, path)
        if not mongo_available:
            install_suggestion = get_protocol_install_suggestion("mongodb")
            raise ImportError("`mongodb` package is missing.\n" + install_suggestion)
        self._mongo = AsyncIOMotorClient(self.full_path, uuidRepresentation="standard")
        db = self._mongo.get_default_database()

        self.collections = {
            self._CONTEXTS_TABLE: db[f"{collection_prefix}_{self._CONTEXTS_TABLE}"],
            self._LOGS_TABLE: db[f"{collection_prefix}_{self._LOGS_TABLE}"],
        }

        asyncio.run(
            asyncio.gather(
                self.collections[self._CONTEXTS_TABLE].create_index([(ExtraFields.primary_id.value, ASCENDING)], background=True, unique=True),
                self.collections[self._CONTEXTS_TABLE].create_index([(ExtraFields.storage_key.value, HASHED)], background=True),
                self.collections[self._CONTEXTS_TABLE].create_index([(ExtraFields.active_ctx.value, HASHED)], background=True),
                self.collections[self._LOGS_TABLE].create_index([(ExtraFields.primary_id.value, ASCENDING)], background=True)
            )
        )

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: str):
        await self.collections[self._CONTEXTS_TABLE].update_many({ExtraFields.active_ctx.value: True, ExtraFields.storage_key.value: key}, {"$set": {ExtraFields.active_ctx.value: False}})

    @threadsafe_method
    async def len_async(self) -> int:
        return len(await self.collections[self._CONTEXTS_TABLE].distinct(ExtraFields.storage_key.value, {ExtraFields.active_ctx.value: True}))

    @threadsafe_method
    async def clear_async(self):
        await self.collections[self._CONTEXTS_TABLE].update_many({ExtraFields.active_ctx.value: True}, {"$set": {ExtraFields.active_ctx.value: False}})

    @threadsafe_method
    @cast_key_to_string()
    async def _get_last_ctx(self, key: str) -> Optional[str]:
        last_ctx = await self.collections[self._CONTEXTS_TABLE].find_one({ExtraFields.active_ctx.value: True, ExtraFields.storage_key.value: key})
        return last_ctx[ExtraFields.primary_id.value] if last_ctx is not None else None

    async def _read_pac_ctx(self, _: str, primary_id: str) -> Dict:
        packed = await self.collections[self._CONTEXTS_TABLE].find_one({ExtraFields.primary_id.value: primary_id}, [self._PACKED_COLUMN])
        return pickle.loads(packed[self._PACKED_COLUMN])

    async def _read_log_ctx(self, keys_limit: Optional[int], keys_offset: int, field_name: str, primary_id: str) -> Dict:
        keys_word = "keys"
        keys = await self.collections[self._LOGS_TABLE].aggregate([
            {"$match": {ExtraFields.primary_id.value: primary_id, field_name: {"$exists": True}}},
            {"$project": {field_name: 1, "objs": {"$objectToArray": f"${field_name}"}}},
            {"$project": {keys_word: "$objs.k"}}
        ]).to_list(None)

        if len(keys) == 0:
            return dict()
        keys = sorted([int(key) for key in keys[0][keys_word]], reverse=True)
        keys = keys[keys_offset:] if keys_limit is None else keys[keys_offset:keys_offset+keys_limit]

        results = await self.collections[self._LOGS_TABLE].aggregate([
            {"$match": {ExtraFields.primary_id.value: primary_id, field_name: {"$exists": True}}},
            {"$project": {field_name: 1, "objs": {"$objectToArray": f"${field_name}"}}},
            {"$unwind": "$objs"},
            {"$project": {self._KEY_COLUMN: {"$toInt": "$objs.k"}, self._VALUE_COLUMN: f"$objs.v.{self._VALUE_COLUMN}"}},
            {"$project": {self._KEY_COLUMN: 1, self._VALUE_COLUMN: 1, "included": {"$in": ["$key", keys]}}},
            {"$match": {"included": True}}
        ]).to_list(None)
        return {result[self._KEY_COLUMN]: pickle.loads(result[self._VALUE_COLUMN]) for result in results}

    async def _write_pac_ctx(self, data: Dict, storage_key: str, primary_id: str):
        now = datetime.datetime.now()
        await self.collections[self._CONTEXTS_TABLE].update_one(
            {ExtraFields.primary_id.value: primary_id},
            [{"$set": {
                self._PACKED_COLUMN: pickle.dumps(data),
                ExtraFields.storage_key.value: storage_key,
                ExtraFields.primary_id.value: primary_id,
                ExtraFields.active_ctx.value: True, 
                ExtraFields.created_at.value: {"$cond": [{"$not": [f"${ExtraFields.created_at.value}"]}, now, f"${ExtraFields.created_at.value}"]},
                ExtraFields.updated_at.value: now
            }}],
            upsert=True
        )

    async def _write_log_ctx(self, data: List[Tuple[str, int, Any]], primary_id: str):
        now = datetime.datetime.now()
        await self.collections[self._LOGS_TABLE].bulk_write([
            UpdateOne({
                ExtraFields.primary_id.value: primary_id
            }, [{"$set": {
                ExtraFields.primary_id.value: primary_id,
                f"{field}.{key}.{self._VALUE_COLUMN}": pickle.dumps(value),
                f"{field}.{key}.{ExtraFields.created_at.value}": {"$cond": [{"$not": [f"${ExtraFields.created_at.value}"]}, now, f"${ExtraFields.created_at.value}"]},
                f"{field}.{key}.{ExtraFields.updated_at.value}": now
            }}], upsert=True)
        for field, key, value in data])
