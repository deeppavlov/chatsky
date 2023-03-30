"""
Mongo
-----
The Mongo module provides a MongoDB-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a MongoDB.
It allows the `DFF` to easily store and retrieve context data in a format that is highly scalable
and easy to work with.

MongoDB is a widely-used, open-source NoSQL database that is known for its scalability and performance.
It stores data in a format similar to JSON, making it easy to work with the data in a variety of programming languages
and environments. Additionally, MongoDB is highly scalable and can handle large amounts of data
and high levels of read and write traffic.

TODO: remove explicit id and timestamp
"""
import json
import logging
import time
from typing import Hashable, Dict, Union, Optional

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
from .update_scheme import full_update_scheme, UpdateScheme, UpdateSchemeBuilder, FieldRule, AdditionalFields

logger = logging.getLogger(__name__)


class MongoContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `mongodb` as the database backend.

    :param path: Database URI. Example: `mongodb://user:password@host:port/dbname`.
    :param collection: Name of the collection to store the data in.
    """

    _CONTEXTS = "contexts"
    _KEY_NONE = "null"

    def __init__(self, path: str, collection_prefix: str = "dff_collection"):
        DBContextStorage.__init__(self, path)
        if not mongo_available:
            install_suggestion = get_protocol_install_suggestion("mongodb")
            raise ImportError("`mongodb` package is missing.\n" + install_suggestion)
        self._mongo = AsyncIOMotorClient(self.full_path, uuidRepresentation="standard")
        db = self._mongo.get_default_database()
        self._prf = collection_prefix
        self.collections = {field: db[f"{self._prf}_{field}"] for field in full_update_scheme.keys()}
        self.collections.update({self._CONTEXTS: db[f"{self._prf}_contexts"]})

    def set_update_scheme(self, scheme: Union[UpdateScheme, UpdateSchemeBuilder]):
        super().set_update_scheme(scheme)
        self.update_scheme.fields[AdditionalFields.IDENTITY_FIELD].update(write=FieldRule.UPDATE_ONCE)
        self.update_scheme.fields.setdefault(AdditionalFields.EXTERNAL_FIELD, dict()).update(write=FieldRule.UPDATE_ONCE)
        self.update_scheme.fields.setdefault(AdditionalFields.CREATED_AT_FIELD, dict()).update(write=FieldRule.UPDATE_ONCE)
        logger.warning(f"init -> {self.update_scheme.fields}")

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        last_context = await self.collections[self._CONTEXTS].find({AdditionalFields.EXTERNAL_FIELD: key}).sort(AdditionalFields.CREATED_AT_FIELD, -1).to_list(1)
        if len(last_context) == 0 or self._check_none(last_context[0]) is None:
            raise KeyError(f"No entry for key {key}.")
        last_context[0]["id"] = last_context[0][AdditionalFields.IDENTITY_FIELD]
        logger.warning(f"read -> {key}: {last_context[0]} {last_context[0]['id']}")
        return Context.cast(last_context[0])

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        identifier = {**json.loads(value.json()), AdditionalFields.EXTERNAL_FIELD: key, AdditionalFields.IDENTITY_FIELD: value.id, AdditionalFields.CREATED_AT_FIELD: time.time_ns()}
        last_context = await self.collections[self._CONTEXTS].find({AdditionalFields.EXTERNAL_FIELD: key}).sort(AdditionalFields.CREATED_AT_FIELD, -1).to_list(1)
        if len(last_context) != 0 and self._check_none(last_context[0]) is None:
            await self.collections[self._CONTEXTS].replace_one({AdditionalFields.IDENTITY_FIELD: last_context[0][AdditionalFields.IDENTITY_FIELD]}, identifier, upsert=True)
        else:
            await self.collections[self._CONTEXTS].insert_one(identifier)
        logger.warning(f"write -> {key}: {identifier} {value.id}")

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def del_item_async(self, key: Union[Hashable, str]):
        await self.collections[self._CONTEXTS].insert_one({AdditionalFields.EXTERNAL_FIELD: key, AdditionalFields.CREATED_AT_FIELD: time.time_ns(), self._KEY_NONE: True})

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        last_context = await self.collections[self._CONTEXTS].find({AdditionalFields.EXTERNAL_FIELD: key}).sort(AdditionalFields.CREATED_AT_FIELD, -1).to_list(1)
        return len(last_context) != 0 and self._check_none(last_context[0]) is not None

    @threadsafe_method
    async def len_async(self) -> int:
        return len(await self.collections[self._CONTEXTS].distinct(AdditionalFields.EXTERNAL_FIELD, {self._KEY_NONE: {"$ne": True}}))

    @threadsafe_method
    async def clear_async(self):
        for collection in self.collections.values():
            await collection.delete_many(dict())

    @classmethod
    def _check_none(cls, value: Dict) -> Optional[Dict]:
        return None if value.get(cls._KEY_NONE, False) else value
