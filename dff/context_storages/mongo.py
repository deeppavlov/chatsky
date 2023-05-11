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
from typing import Hashable, Dict, Union, Optional, Tuple, List, Any

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson.objectid import ObjectId

    mongo_available = True
except ImportError:
    mongo_available = False
    AsyncIOMotorClient = None
    ObjectId = None

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, auto_stringify_hashable_key
from .protocol import get_protocol_install_suggestion
from .update_scheme import UpdateScheme, FieldRule, ValueField, ExtraFields


class MongoContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `mongodb` as the database backend.

    :param path: Database URI. Example: `mongodb://user:password@host:port/dbname`.
    :param collection: Name of the collection to store the data in.
    """

    _CONTEXTS = "contexts"
    _KEY_KEY = "key"
    _KEY_VALUE = "value"

    def __init__(self, path: str, collection_prefix: str = "dff_collection"):
        DBContextStorage.__init__(self, path)
        if not mongo_available:
            install_suggestion = get_protocol_install_suggestion("mongodb")
            raise ImportError("`mongodb` package is missing.\n" + install_suggestion)
        self._mongo = AsyncIOMotorClient(self.full_path, uuidRepresentation="standard")
        db = self._mongo.get_default_database()

        self.seq_fields = [
            field for field, field_props in dict(self.update_scheme).items() if not isinstance(field_props, ValueField)
        ]
        self.collections = {field: db[f"{collection_prefix}_{field}"] for field in self.seq_fields}
        self.collections.update({self._CONTEXTS: db[f"{collection_prefix}_contexts"]})

    def set_update_scheme(self, scheme: UpdateScheme):
        super().set_update_scheme(scheme)
        self.update_scheme.id.on_write = FieldRule.UPDATE_ONCE
        self.update_scheme.ext_id.on_write = FieldRule.UPDATE_ONCE
        self.update_scheme.created_at.on_write = FieldRule.UPDATE_ONCE

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        fields, int_id = await self._read_keys(key)
        if int_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.update_scheme.read_context(fields, self._read_ctx, key, int_id)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        fields, _ = await self._read_keys(key)
        value_hash = self.hash_storage.get(key, None)
        await self.update_scheme.write_context(value, value_hash, fields, self._write_ctx, key)

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def del_item_async(self, key: Union[Hashable, str]):
        await self.collections[self._CONTEXTS].insert_one(
            {
                self.update_scheme.id.name: None,
                self.update_scheme.ext_id.name: key,
                self.update_scheme.created_at.name: time.time_ns(),
            }
        )

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        last_context = (
            await self.collections[self._CONTEXTS]
            .find({self.update_scheme.ext_id.name: key})
            .sort(self.update_scheme.created_at.name, -1)
            .to_list(1)
        )
        return len(last_context) != 0 and self._check_none(last_context[-1]) is not None

    @threadsafe_method
    async def len_async(self) -> int:
        return len(
            await self.collections[self._CONTEXTS].distinct(
                self.update_scheme.ext_id.name, {self.update_scheme.id.name: {"$ne": None}}
            )
        )

    @threadsafe_method
    async def clear_async(self):
        external_keys = await self.collections[self._CONTEXTS].distinct(self.update_scheme.ext_id.name)
        documents_common = {self.update_scheme.id.name: None, self.update_scheme.created_at.name: time.time_ns()}
        documents = [dict(**documents_common, **{self.update_scheme.ext_id.name: key}) for key in external_keys]
        if len(documents) > 0:
            await self.collections[self._CONTEXTS].insert_many(documents)

    @classmethod
    def _check_none(cls, value: Dict) -> Optional[Dict]:
        return None if value.get(ExtraFields.id, None) is None else value

    async def _read_keys(self, ext_id: str) -> Tuple[Dict[str, List[str]], Optional[str]]:
        key_dict = dict()
        last_context = (
            await self.collections[self._CONTEXTS]
            .find({self.update_scheme.ext_id.name: ext_id})
            .sort(self.update_scheme.created_at.name, -1)
            .to_list(1)
        )
        if len(last_context) == 0:
            return key_dict, None
        last_id = last_context[-1][self.update_scheme.id.name]
        for name, collection in [(field, self.collections[field]) for field in self.seq_fields]:
            key_dict[name] = await collection.find({self.update_scheme.id.name: last_id}).distinct(self._KEY_KEY)
        return key_dict, last_id

    async def _read_ctx(self, subscript: Dict[str, Union[bool, Dict[Hashable, bool]]], int_id: str, _: str) -> Dict:
        result_dict = dict()
        for field in [field for field, value in subscript.items() if isinstance(value, dict) and len(value) > 0]:
            for key in [key for key, value in subscript[field].items() if value]:
                value = (
                    await self.collections[field]
                    .find({self.update_scheme.id.name: int_id, self._KEY_KEY: key})
                    .to_list(1)
                )
                if len(value) > 0 and value[-1] is not None:
                    if field not in result_dict:
                        result_dict[field] = dict()
                    result_dict[field][key] = value[-1][self._KEY_VALUE]
        value = await self.collections[self._CONTEXTS].find({self.update_scheme.id.name: int_id}).to_list(1)
        if len(value) > 0 and value[-1] is not None:
            result_dict = {**value[-1], **result_dict}
        return result_dict

    async def _write_ctx(self, data: Dict[str, Any], int_id: str, _: str):
        for field in [field for field, value in data.items() if isinstance(value, dict) and len(value) > 0]:
            for key in [key for key, value in data[field].items() if value]:
                identifier = {self.update_scheme.id.name: int_id, self._KEY_KEY: key}
                await self.collections[field].update_one(
                    identifier, {"$set": {**identifier, self._KEY_VALUE: data[field][key]}}, upsert=True
                )
        ctx_data = {field: value for field, value in data.items() if not isinstance(value, dict)}
        await self.collections[self._CONTEXTS].update_one(
            {self.update_scheme.id.name: int_id}, {"$set": ctx_data}, upsert=True
        )
