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
from typing import Dict, Set, Tuple, Optional, List, Any

try:
    from pymongo import ASCENDING, HASHED, UpdateOne
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_available = True
except ImportError:
    mongo_available = False

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from .protocol import get_protocol_install_suggestion
from .context_schema import ContextSchema, ExtraFields
from .serializer import DefaultSerializer


class MongoContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `mongodb` as the database backend.

    CONTEXTS table is stored as `COLLECTION_PREFIX_contexts` collection.
    LOGS table is stored as `COLLECTION_PREFIX_logs` collection.

    :param path: Database URI. Example: `mongodb://user:password@host:port/dbname`.
    :param context_schema: Context schema for this storage.
    :param serializer: Serializer that will be used for serializing contexts.
    :param collection_prefix: "namespace" prefix for the two collections created for context storing.
    """

    _CONTEXTS_TABLE = "contexts"
    _LOGS_TABLE = "logs"
    _KEY_COLUMN = "key"
    _VALUE_COLUMN = "value"
    _FIELD_COLUMN = "field"
    _PACKED_COLUMN = "data"

    def __init__(
        self,
        path: str,
        context_schema: Optional[ContextSchema] = None,
        serializer: Any = DefaultSerializer(),
        collection_prefix: str = "dff_collection",
    ):
        DBContextStorage.__init__(self, path, context_schema, serializer)
        self.context_schema.supports_async = True

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
                self.collections[self._CONTEXTS_TABLE].create_index(
                    [(ExtraFields.primary_id.value, ASCENDING)], background=True, unique=True
                ),
                self.collections[self._CONTEXTS_TABLE].create_index(
                    [(ExtraFields.storage_key.value, HASHED)], background=True
                ),
                self.collections[self._CONTEXTS_TABLE].create_index(
                    [(ExtraFields.active_ctx.value, HASHED)], background=True
                ),
                self.collections[self._LOGS_TABLE].create_index(
                    [(ExtraFields.primary_id.value, ASCENDING)], background=True
                ),
            )
        )

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: str):
        await self.collections[self._CONTEXTS_TABLE].update_many(
            {ExtraFields.storage_key.value: key}, {"$set": {ExtraFields.active_ctx.value: False}}
        )

    @threadsafe_method
    async def len_async(self) -> int:
        count_key = "unique_count"
        unique = (
            await self.collections[self._CONTEXTS_TABLE]
            .aggregate(
                [
                    {"$match": {ExtraFields.active_ctx.value: True}},
                    {"$group": {"_id": None, "unique_keys": {"$addToSet": f"${ExtraFields.storage_key.value}"}}},
                    {"$project": {count_key: {"$size": "$unique_keys"}}},
                ]
            )
            .to_list(1)
        )
        return 0 if len(unique) == 0 else unique[0][count_key]

    @threadsafe_method
    async def clear_async(self, prune_history: bool = False):
        if prune_history:
            await self.collections[self._CONTEXTS_TABLE].drop()
            await self.collections[self._LOGS_TABLE].drop()
        else:
            await self.collections[self._CONTEXTS_TABLE].update_many(
                {}, {"$set": {ExtraFields.active_ctx.value: False}}
            )

    @threadsafe_method
    async def keys_async(self) -> Set[str]:
        unique_key = "unique_keys"
        unique = (
            await self.collections[self._CONTEXTS_TABLE]
            .aggregate(
                [
                    {"$match": {ExtraFields.active_ctx.value: True}},
                    {"$group": {"_id": None, unique_key: {"$addToSet": f"${ExtraFields.storage_key.value}"}}},
                ]
            )
            .to_list(None)
        )
        return set(unique[0][unique_key])

    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        return (
            await self.collections[self._CONTEXTS_TABLE].count_documents(
                {"$and": [{ExtraFields.storage_key.value: key}, {ExtraFields.active_ctx.value: True}]}
            )
            > 0
        )

    async def _read_pac_ctx(self, storage_key: str) -> Tuple[Dict, Optional[str]]:
        packed = await self.collections[self._CONTEXTS_TABLE].find_one(
            {"$and": [{ExtraFields.storage_key.value: storage_key}, {ExtraFields.active_ctx.value: True}]},
            [self._PACKED_COLUMN, ExtraFields.primary_id.value],
            sort=[(ExtraFields.updated_at.value, -1)],
        )
        if packed is not None:
            return self.serializer.loads(packed[self._PACKED_COLUMN]), packed[ExtraFields.primary_id.value]
        else:
            return dict(), None

    async def _read_log_ctx(self, keys_limit: Optional[int], field_name: str, primary_id: str) -> Dict:
        logs = (
            await self.collections[self._LOGS_TABLE]
            .find(
                {"$and": [{ExtraFields.primary_id.value: primary_id}, {self._FIELD_COLUMN: field_name}]},
                [self._KEY_COLUMN, self._VALUE_COLUMN],
                sort=[(self._KEY_COLUMN, -1)],
                limit=keys_limit if keys_limit is not None else 0,
            )
            .to_list(None)
        )
        return {log[self._KEY_COLUMN]: self.serializer.loads(log[self._VALUE_COLUMN]) for log in logs}

    async def _write_pac_ctx(self, data: Dict, created: int, updated: int, storage_key: str, primary_id: str):
        await self.collections[self._CONTEXTS_TABLE].update_one(
            {ExtraFields.primary_id.value: primary_id},
            {
                "$set": {
                    ExtraFields.active_ctx.value: True,
                    self._PACKED_COLUMN: self.serializer.dumps(data),
                    ExtraFields.storage_key.value: storage_key,
                    ExtraFields.primary_id.value: primary_id,
                    ExtraFields.created_at.value: created,
                    ExtraFields.updated_at.value: updated,
                }
            },
            upsert=True,
        )

    async def _write_log_ctx(self, data: List[Tuple[str, int, Dict]], updated: int, primary_id: str):
        await self.collections[self._LOGS_TABLE].bulk_write(
            [
                UpdateOne(
                    {
                        "$and": [
                            {ExtraFields.primary_id.value: primary_id},
                            {self._FIELD_COLUMN: field},
                            {self._KEY_COLUMN: key},
                        ]
                    },
                    {
                        "$set": {
                            self._FIELD_COLUMN: field,
                            self._KEY_COLUMN: key,
                            self._VALUE_COLUMN: self.serializer.dumps(value),
                            ExtraFields.primary_id.value: primary_id,
                            ExtraFields.updated_at.value: updated,
                        }
                    },
                    upsert=True,
                )
                for field, key, value in data
            ]
        )
