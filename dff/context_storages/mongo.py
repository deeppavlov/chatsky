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
"""
import json
from typing import Hashable, Dict, Union, List, Any, Optional
from uuid import UUID

from .update_scheme import full_update_scheme

try:
    from motor.motor_asyncio import AsyncIOMotorClient

    mongo_available = True
except ImportError:
    mongo_available = False
    AsyncIOMotorClient = None

from dff.script import Context

from .database import DBContextStorage, threadsafe_method
from .protocol import get_protocol_install_suggestion


class MongoContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `mongodb` as the database backend.

    :param path: Database URI. Example: `mongodb://user:password@host:port/dbname`.
    :param collection: Name of the collection to store the data in.
    """

    _EXTERNAL = "_ext_id"
    _INTERNAL = "_int_id"

    _CONTEXTS = "contexts"
    _KEY_NONE = "null"

    def __init__(self, path: str, collection_prefix: str = "dff_collection"):
        DBContextStorage.__init__(self, path)
        if not mongo_available:
            install_suggestion = get_protocol_install_suggestion("mongodb")
            raise ImportError("`mongodb` package is missing.\n" + install_suggestion)
        self._mongo = AsyncIOMotorClient(self.full_path, uuidRepresentation='standard')
        db = self._mongo.get_default_database()
        self._prf = collection_prefix
        self.collections = {field: db[f"{self._prf}_{field}"] for field in full_update_scheme.write_fields}
        self.collections.update({self._CONTEXTS: db[f"{self._prf}_contexts"]})

    @threadsafe_method
    async def get_item_async(self, key: Hashable) -> Context:
        last_context = await self.collections[self._CONTEXTS].find({self._EXTERNAL: str(key)}).sort(self._INTERNAL, 1).to_list(1)
        if len(last_context) == 0 or self._check_none(last_context[0]) is None:
            raise KeyError(f"No entry for key {key}.")
        last_context[0]["id"] = last_context[0][self._INTERNAL]
        return Context.cast({k: v for k, v in last_context[0].items() if k not in (self._INTERNAL, self._EXTERNAL)})

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        identifier = {self._EXTERNAL: str(key), self._INTERNAL: value.id}
        await self.collections[self._CONTEXTS].replace_one(identifier, {**json.loads(value.json()), **identifier}, upsert=True)

    @threadsafe_method
    async def del_item_async(self, key: Hashable):
        await self.collections[self._CONTEXTS].insert_one({self._EXTERNAL: key, self._KEY_NONE: True})

    @threadsafe_method
    async def contains_async(self, key: Hashable) -> bool:
        last_context = await self.collections[self._CONTEXTS].find({self._EXTERNAL: key}).sort(self._INTERNAL, 1).to_list(1)
        return len(last_context) != 0 and self._check_none(last_context[0]) is not None

    @threadsafe_method
    async def len_async(self) -> int:
        return len(await self.collections[self._CONTEXTS].distinct(self._EXTERNAL, {self._KEY_NONE: {"$ne": True}}))

    @threadsafe_method
    async def clear_async(self):
        for collection in self.collections.values():
            await collection.delete_many(dict())

    @classmethod
    def _check_none(cls, value: Dict) -> Optional[Dict]:
        return None if value.get(cls._KEY_NONE, False) else value

    async def _read_fields(self, field_name: str, int_id: Union[UUID, int, str], ext_id: Union[UUID, int, str]) -> List[str]:
        result = list()
        for key in await self._redis.keys(f"{ext_id}:{int_id}:{field_name}:*"):
            res = key.decode().split(":")[-1]
            result += [int(res) if res.isdigit() else res]
        return result

    async def _read_seq(self, field_name: str, outlook: List[Hashable], int_id: Union[UUID, int, str], ext_id: Union[UUID, int, str]) -> Dict[Hashable, Any]:
        result = dict()
        for key in outlook:
            value = await self._redis.get(f"{ext_id}:{int_id}:{field_name}:{key}")
            result[key] = pickle.loads(value) if value is not None else None
        return result

    async def _read_value(self, field_name: str, int_id: Union[UUID, int, str], ext_id: Union[UUID, int, str]) -> Any:
        value = await self._redis.get(f"{ext_id}:{int_id}:{field_name}")
        return pickle.loads(value) if value is not None else None

    async def _write_seq(self, field_name: str, data: Dict[Hashable, Any], int_id: Union[UUID, int, str], ext_id: Union[UUID, int, str]):
        for key, value in data.items():
            await self._redis.set(f"{ext_id}:{int_id}:{field_name}:{key}", pickle.dumps(value))

    async def _write_value(self, data: Any, field_name: str, int_id: Union[UUID, int, str], ext_id: Union[UUID, int, str]):
        return await self._redis.set(f"{ext_id}:{int_id}:{field_name}", pickle.dumps(data))

