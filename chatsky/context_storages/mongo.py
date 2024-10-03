"""
Mongo
-----
The Mongo module provides a MongoDB-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a MongoDB.
It allows Chatsky to easily store and retrieve context data in a format that is highly scalable
and easy to work with.

MongoDB is a widely-used, open-source NoSQL database that is known for its scalability and performance.
It stores data in a format similar to JSON, making it easy to work with the data in a variety of programming languages
and environments. Additionally, MongoDB is highly scalable and can handle large amounts of data
and high levels of read and write traffic.
"""

import asyncio
from typing import Dict, Hashable, Set, Tuple, Optional, List, Any

try:
    from pymongo import ASCENDING, HASHED, UpdateOne
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_available = True
except ImportError:
    mongo_available = False

from .database import DBContextStorage, FieldConfig
from .protocol import get_protocol_install_suggestion


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

    _UNIQUE_KEYS = "unique_keys"

    _KEY_COLUMN = "key"
    _VALUE_COLUMN = "value"

    is_asynchronous = False

    def __init__(
        self,
        path: str,
        serializer: Optional[Any] = None,
        rewrite_existing: bool = False,
        turns_config: Optional[FieldConfig] = None,
        misc_config: Optional[FieldConfig] = None,
        collection_prefix: str = "chatsky_collection",
    ):
        DBContextStorage.__init__(self, path, serializer, rewrite_existing, turns_config, misc_config)

        if not mongo_available:
            install_suggestion = get_protocol_install_suggestion("mongodb")
            raise ImportError("`mongodb` package is missing.\n" + install_suggestion)
        self._mongo = AsyncIOMotorClient(self.full_path, uuidRepresentation="standard")
        db = self._mongo.get_default_database()

        self._main_table = db[f"{collection_prefix}_{self._main_table_name}"],
        self._turns_table = db[f"{collection_prefix}_{self._turns_table_name}"]
        self._misc_table = db[f"{collection_prefix}_{self._misc_table_name}"]

        asyncio.run(
            asyncio.gather(
                self._main_table.create_index(
                    [(self._id_column_name, ASCENDING)], background=True, unique=True
                ),
                self._turns_table.create_index(
                    [(self._id_column_name, self._KEY_COLUMN, HASHED)], background=True, unique=True
                ),
                self._misc_table.create_index(
                    [(self._id_column_name, self._KEY_COLUMN, HASHED)], background=True, unique=True
                ),
            )
        )

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes]]:
        result = await self._main_table.find_one(
            {self._id_column_name: ctx_id},
            [self._current_turn_id_column_name, self._created_at_column_name, self._updated_at_column_name, self._framework_data_column_name]
        )
        return result.values() if result is not None else None

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, fw_data: bytes) -> None:
        await self._main_table.update_one(
            {self._id_column_name: ctx_id},
            {
                "$set": {
                    self._id_column_name: ctx_id,
                    self._current_turn_id_column_name: turn_id,
                    self._created_at_column_name: crt_at,
                    self._updated_at_column_name: upd_at,
                    self._framework_data_column_name: fw_data,
                }
            },
            upsert=True,
        )

    async def delete_main_info(self, ctx_id: str) -> None:
        await self._main_table.delete_one({self._id_column_name: ctx_id})

    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[Hashable, bytes]]:
        return self._turns_table.find(
            {self._id_column_name: ctx_id},
            [self._KEY_COLUMN, field_name],
            sort=[(self._KEY_COLUMN, -1)],
        ).to_list(None)

    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[Hashable]:
        keys = self._turns_table.aggregate(
            [
                {"$match": {self._id_column_name: ctx_id}},
                {"$group": {"_id": None, self._UNIQUE_KEYS: {"$addToSet": f"${self._KEY_COLUMN}"}}},
            ]
        ).to_list(None)
        return set(keys[0][self._UNIQUE_KEYS])

    async def load_field_items(self, ctx_id: str, field_name: str, keys: Set[Hashable]) -> List[bytes]:
        return self._turns_table.find(
            {self._id_column_name: ctx_id},
            [self._KEY_COLUMN, field_name],
            sort=[(self._KEY_COLUMN, -1)],
        ).to_list(None)
        ## TODO:!!

    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[Hashable, bytes]]) -> None:
        await self._turns_table.update_one(
            {self._id_column_name: ctx_id, self._KEY_COLUMN: field_name},
            {
                "$set": {
                    self._KEY_COLUMN: field_name,
                    self._PACKED_COLUMN: self.serializer.dumps(data),
                    ExtraFields.storage_key.value: storage_key,
                    ExtraFields.id.value: id,
                    ExtraFields.created_at.value: created,
                    ExtraFields.updated_at.value: updated,
                }
            },
            upsert=True,
        )

    async def clear_all(self) -> None:
        """
        Clear all the chatsky tables and records.
        """
        raise NotImplementedError









    async def del_item_async(self, key: str):
        await self.collections[self._CONTEXTS_TABLE].update_many(
            {ExtraFields.storage_key.value: key}, {"$set": {ExtraFields.active_ctx.value: False}}
        )

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

    async def clear_async(self, prune_history: bool = False):
        if prune_history:
            await self.collections[self._CONTEXTS_TABLE].drop()
            await self.collections[self._LOGS_TABLE].drop()
        else:
            await self.collections[self._CONTEXTS_TABLE].update_many(
                {}, {"$set": {ExtraFields.active_ctx.value: False}}
            )

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
            [self._PACKED_COLUMN, ExtraFields.id.value],
            sort=[(ExtraFields.updated_at.value, -1)],
        )
        if packed is not None:
            return self.serializer.loads(packed[self._PACKED_COLUMN]), packed[ExtraFields.id.value]
        else:
            return dict(), None

    async def _read_log_ctx(self, keys_limit: Optional[int], field_name: str, id: str) -> Dict:
        logs = (
            await self.collections[self._LOGS_TABLE]
            .find(
                {"$and": [{ExtraFields.id.value: id}, {self._FIELD_COLUMN: field_name}]},
                [self._KEY_COLUMN, self._VALUE_COLUMN],
                sort=[(self._KEY_COLUMN, -1)],
                limit=keys_limit if keys_limit is not None else 0,
            )
            .to_list(None)
        )
        return {log[self._KEY_COLUMN]: self.serializer.loads(log[self._VALUE_COLUMN]) for log in logs}

    async def _write_pac_ctx(self, data: Dict, created: int, updated: int, storage_key: str, id: str):
        await self.collections[self._CONTEXTS_TABLE].update_one(
            {ExtraFields.id.value: id},
            {
                "$set": {
                    ExtraFields.active_ctx.value: True,
                    self._PACKED_COLUMN: self.serializer.dumps(data),
                    ExtraFields.storage_key.value: storage_key,
                    ExtraFields.id.value: id,
                    ExtraFields.created_at.value: created,
                    ExtraFields.updated_at.value: updated,
                }
            },
            upsert=True,
        )

    async def _write_log_ctx(self, data: List[Tuple[str, int, Dict]], updated: int, id: str):
        await self.collections[self._LOGS_TABLE].bulk_write(
            [
                UpdateOne(
                    {
                        "$and": [
                            {ExtraFields.id.value: id},
                            {self._FIELD_COLUMN: field},
                            {self._KEY_COLUMN: key},
                        ]
                    },
                    {
                        "$set": {
                            self._FIELD_COLUMN: field,
                            self._KEY_COLUMN: key,
                            self._VALUE_COLUMN: self.serializer.dumps(value),
                            ExtraFields.id.value: id,
                            ExtraFields.updated_at.value: updated,
                        }
                    },
                    upsert=True,
                )
                for field, key, value in data
            ]
        )
