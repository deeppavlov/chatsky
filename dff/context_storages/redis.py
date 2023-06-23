"""
Redis
-----
The Redis module provides a Redis-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a Redis.
It allows the DFF to easily store and retrieve context data in a format that is highly scalable
and easy to work with.

Redis is an open-source, in-memory data structure store that is known for its
high performance and scalability. It stores data in key-value pairs and supports a variety of data
structures such as strings, hashes, lists, sets, and more.
Additionally, Redis can be used as a cache, message broker, and database, making it a versatile
and powerful choice for data storage and management.
"""
import pickle
from typing import Hashable, List, Dict, Union, Optional

try:
    from redis.asyncio import Redis

    redis_available = True
except ImportError:
    redis_available = False
    Redis = None

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from .context_schema import ALL_ITEMS, ContextSchema, ExtraFields
from .protocol import get_protocol_install_suggestion


class RedisContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `redis` as the database backend.

    The relations between primary identifiers and active context storage keys are stored
    as a redis hash ("KEY_PREFIX:index").

    That's how context fields are stored:
    `"KEY_PREFIX:data:PRIMARY_ID:FIELD": "DATA"`
    That's how context dictionary fields are stored:
    `"KEY_PREFIX:data:PRIMARY_ID:FIELD:KEY": "DATA"`
    For serialization of non-string data types `pickle` module is used.

    :param path: Database URI string. Example: `redis://user:password@host:port`.
    """

    _INDEX_TABLE = "index"
    _DATA_TABLE = "data"

    def __init__(self, path: str, key_prefix: str = "dff_keys"):
        DBContextStorage.__init__(self, path)
        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        self._redis = Redis.from_url(self.full_path)
        self._index_key = f"{key_prefix}:{self._INDEX_TABLE}"
        self._data_key = f"{key_prefix}:{self._DATA_TABLE}"

    def set_context_schema(self, scheme: ContextSchema):
        super().set_context_schema(scheme)
        params = {
            **self.context_schema.dict(),
            "active_ctx": FrozenValueSchemaField(name=ExtraFields.active_ctx, on_write=SchemaFieldWritePolicy.IGNORE),
        }
        self.context_schema = ContextSchema(**params)

    @threadsafe_method
    @cast_key_to_string()
    async def get_item_async(self, key: str) -> Context:
        primary_id = await self._get_last_ctx(key)
        if primary_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.context_schema.read_context(self._read_ctx, key, primary_id)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @cast_key_to_string()
    async def set_item_async(self, key: str, value: Context):
        primary_id = await self._get_last_ctx(key)
        value_hash = self.hash_storage.get(key)
        primary_id = await self.context_schema.write_context(value, value_hash, self._write_ctx_val, key, primary_id)
        await self._redis.hset(self._index_key, key, primary_id)

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: str):
        self.hash_storage[key] = None
        if await self._get_last_ctx(key) is None:
            raise KeyError(f"No entry for key {key}.")
        await self._redis.hdel(self._index_key, key)

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        return await self._redis.hexists(self._index_key, key)

    @threadsafe_method
    async def len_async(self) -> int:
        return len(await self._redis.hkeys(self._index_key))

    @threadsafe_method
    async def clear_async(self):
        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        await self._redis.delete(self._index_key)

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        last_primary_id = await self._redis.hget(self._index_key, storage_key)
        return last_primary_id.decode() if last_primary_id is not None else None

    async def _read_ctx(self, subscript: Dict[str, Union[bool, int, List[Hashable]]], primary_id: str) -> Dict:
        context = dict()
        for key, value in subscript.items():
            if isinstance(value, bool) and value:
                raw_value = await self._redis.get(f"{self._data_key}:{primary_id}:{key}")
                context[key] = pickle.loads(raw_value) if raw_value is not None else None
            else:
                value_fields = await self._redis.keys(f"{self._data_key}:{primary_id}:{key}:*")
                value_field_names = [value_key.decode().split(":")[-1] for value_key in value_fields]
                if isinstance(value, int):
                    value_field_names = sorted([int(key) for key in value_field_names])[value:]
                elif isinstance(value, list):
                    value_field_names = [key for key in value_field_names if key in value]
                elif value != ALL_ITEMS:
                    value_field_names = list()
                context[key] = dict()
                for field in value_field_names:
                    raw_value = await self._redis.get(f"{self._data_key}:{primary_id}:{key}:{field}")
                    context[key][field] = pickle.loads(raw_value) if raw_value is not None else None
        return context

    async def _write_ctx_val(self, field: Optional[str], payload: Dict, nested: bool, primary_id: str):
        if nested:
            data, enforce = payload
            for key, value in data.items():
                current_data = await self._redis.get(f"{self._data_key}:{primary_id}:{field}:{key}")
                if enforce or current_data is None:
                    raw_data = pickle.dumps(value)
                    await self._redis.set(f"{self._data_key}:{primary_id}:{field}:{key}", raw_data)
        else:
            for key, (data, enforce) in payload.items():
                current_data = await self._redis.get(f"{self._data_key}:{primary_id}:{key}")
                if enforce or current_data is None:
                    raw_data = pickle.dumps(data)
                    await self._redis.set(f"{self._data_key}:{primary_id}:{key}", raw_data)
