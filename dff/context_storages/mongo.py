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
import time
from typing import Hashable, Dict, Union, Optional, List, Any

try:
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_available = True
except ImportError:
    mongo_available = False
    AsyncIOMotorClient = None
    ObjectId = None

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from .protocol import get_protocol_install_suggestion
from .context_schema import ALL_ITEMS, FieldDescriptor, ValueSchemaField, ExtraFields


class MongoContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `mongodb` as the database backend.

    :param path: Database URI. Example: `mongodb://user:password@host:port/dbname`.
    :param collection: Name of the collection to store the data in.
    """

    _CONTEXTS = "contexts"
    _MISC_KEY = "__mongo_misc_key"
    _ID_KEY = "_id"

    def __init__(self, path: str, collection_prefix: str = "dff_collection"):
        DBContextStorage.__init__(self, path)
        if not mongo_available:
            install_suggestion = get_protocol_install_suggestion("mongodb")
            raise ImportError("`mongodb` package is missing.\n" + install_suggestion)
        self._mongo = AsyncIOMotorClient(self.full_path, uuidRepresentation="standard")
        db = self._mongo.get_default_database()

        self.seq_fields = [
            field
            for field, field_props in dict(self.context_schema).items()
            if not isinstance(field_props, ValueSchemaField)
        ]
        self.collections = {field: db[f"{collection_prefix}_{field}"] for field in self.seq_fields}
        self.collections.update({self._CONTEXTS: db[f"{collection_prefix}_contexts"]})

    @threadsafe_method
    @cast_key_to_string()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.context_schema.read_context(self._read_ctx, key, primary_id)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @cast_key_to_string()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        primary_id = await self._get_last_ctx(key)
        value_hash = self.hash_storage.get(key)
        await self.context_schema.write_context(value, value_hash, self._write_ctx_val, key, primary_id)

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: Union[Hashable, str]):
        self.hash_storage[key] = None
        await self.collections[self._CONTEXTS].update_many(
            {ExtraFields.active_ctx: True, ExtraFields.storage_key: key}, {"$set": {ExtraFields.active_ctx: False}}
        )

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        return await self._get_last_ctx(key) is not None

    @threadsafe_method
    async def len_async(self) -> int:
        return len(
            await self.collections[self._CONTEXTS].distinct(
                self.context_schema.storage_key.name, {ExtraFields.active_ctx: True}
            )
        )

    @threadsafe_method
    async def clear_async(self):
        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        await self.collections[self._CONTEXTS].update_many(
            {ExtraFields.active_ctx: True}, {"$set": {ExtraFields.active_ctx: False}}
        )

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        last_ctx = await self.collections[self._CONTEXTS].find_one(
            {ExtraFields.active_ctx: True, ExtraFields.storage_key: storage_key}
        )
        return last_ctx[ExtraFields.primary_id] if last_ctx is not None else None

    async def _read_ctx(self, subscript: Dict[str, Union[bool, int, List[Hashable]]], primary_id: str) -> Dict:
        primary_id_key = f"{self._MISC_KEY}_{ExtraFields.primary_id}"
        values_slice, result_dict = list(), dict()

        for field, value in subscript.items():
            if isinstance(value, bool) and value:
                values_slice += [field]
            else:
                # AFAIK, we can only read ALL keys and then filter, there's no other way for Mongo :(
                raw_keys = await self.collections[field].aggregate(
                    [
                        { "$match": { primary_id_key: primary_id } },
                        { "$project": { "kvarray": { "$objectToArray": "$$ROOT" } }},
                        { "$project": { "keys": "$kvarray.k" } }
                    ]
                ).to_list(1)
                raw_keys = raw_keys[0]["keys"]

                if isinstance(value, int):
                    filtered_keys = sorted(int(key) for key in raw_keys if key.isdigit())[value:]
                elif isinstance(value, list):
                    filtered_keys = [key for key in raw_keys if key in value]
                elif value == ALL_ITEMS:
                    filtered_keys = raw_keys

                projection = [str(key) for key in filtered_keys if self._MISC_KEY not in str(key) and key != self._ID_KEY]
                if len(projection) > 0:
                    result_dict[field] = await self.collections[field].find_one(
                        {primary_id_key: primary_id}, projection
                    )
                    del result_dict[field][self._ID_KEY]

        values = await self.collections[self._CONTEXTS].find_one(
            {ExtraFields.primary_id: primary_id}, values_slice
        )
        return {**values, **result_dict}

    async def _write_ctx_val(self, field: Optional[str], payload: FieldDescriptor, nested: bool, primary_id: str):
        def conditional_insert(key: Any, value: Dict) -> Dict:
            return { "$cond": [ { "$not": [ f"${key}" ] }, value, f"${key}" ] }
        
        primary_id_key = f"{self._MISC_KEY}_{ExtraFields.primary_id}"
        created_at_key = f"{self._MISC_KEY}_{ExtraFields.created_at}"
        updated_at_key = f"{self._MISC_KEY}_{ExtraFields.updated_at}"

        if nested:
            data, enforce = payload
            for key in data.keys():
                if self._MISC_KEY in str(key):
                    raise RuntimeError(f"Context field {key} keys can't start from {self._MISC_KEY} - that is a reserved key for MongoDB context storage!")
                if key == self._ID_KEY:
                    raise RuntimeError(f"Context field {key} can't contain key {self._ID_KEY} - that is a reserved key for MongoDB!")

            update_value = data if enforce else {str(key): conditional_insert(key, value) for key, value in data.items()}
            update_value.update(
                {
                    primary_id_key: conditional_insert(primary_id_key, primary_id),
                    created_at_key: conditional_insert(created_at_key, time.time_ns()),
                    updated_at_key: time.time_ns()
                }
            )

            await self.collections[field].update_one(
                {primary_id_key: primary_id},
                [ { "$set": update_value } ],
                upsert=True
            )

        else:
            update_value = {key: data if enforce else conditional_insert(key, data) for key, (data, enforce) in payload.items()}
            update_value.update({ExtraFields.updated_at: time.time_ns()})

            await self.collections[self._CONTEXTS].update_one(
                {ExtraFields.primary_id: primary_id},
                [ { "$set": update_value } ],
                upsert=True
            )
