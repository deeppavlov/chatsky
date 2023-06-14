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
    from aioredis import Redis

    redis_available = True
except ImportError:
    redis_available = False
    Redis = None

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from .context_schema import (
    ALL_ITEMS,
    ContextSchema,
    ExtraFields,
    FieldDescriptor,
    FrozenValueSchemaField,
    SchemaFieldWritePolicy,
)
from .protocol import get_protocol_install_suggestion


class RedisContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `redis` as the database backend.

    :param path: Database URI string. Example: `redis://user:password@host:port`.
    """

    _CONTEXTS_KEY = "all_contexts"
    _INDEX_TABLE = "index"
    _DATA_TABLE = "data"

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        self._redis = Redis.from_url(self.full_path)

    def set_context_schema(self, scheme: ContextSchema):
        super().set_context_schema(scheme)
        params = {
            **self.context_schema.dict(),
            "active_ctx": FrozenValueSchemaField(name=ExtraFields.active_ctx, on_write=SchemaFieldWritePolicy.IGNORE),
        }
        self.context_schema = ContextSchema(**params)

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
        primary_id = await self.context_schema.write_context(value, value_hash, self._write_ctx_val, key, primary_id)
        await self._redis.set(f"{self._INDEX_TABLE}:{key}:{ExtraFields.primary_id.value}", primary_id)

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: Union[Hashable, str]):
        self.hash_storage[key] = None
        if await self._get_last_ctx(key) is None:
            raise KeyError(f"No entry for key {key}.")
        await self._redis.delete(f"{self._INDEX_TABLE}:{key}:{ExtraFields.primary_id.value}")

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        primary_key = await self._redis.get(f"{self._INDEX_TABLE}:{key}:{ExtraFields.primary_id.value}")
        return primary_key is not None

    @threadsafe_method
    async def len_async(self) -> int:
        return len(await self._redis.keys(f"{self._INDEX_TABLE}:*"))

    @threadsafe_method
    async def clear_async(self):
        self.hash_storage = {key: None for key, _ in self.hash_storage.items()}
        for key in await self._redis.keys(f"{self._INDEX_TABLE}:*"):
            await self._redis.delete(key)

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        last_primary_id = await self._redis.get(f"{self._INDEX_TABLE}:{storage_key}:{ExtraFields.primary_id.value}")
        return last_primary_id.decode() if last_primary_id is not None else None

    async def _read_ctx(self, subscript: Dict[str, Union[bool, int, List[Hashable]]], primary_id: str) -> Dict:
        context = dict()
        for key, value in subscript.items():
            if isinstance(value, bool) and value:
                raw_value = await self._redis.get(f"{self._DATA_TABLE}:{primary_id}:{key}")
                context[key] = pickle.loads(raw_value) if raw_value is not None else None
            else:
                value_fields = await self._redis.keys(f"{self._DATA_TABLE}:{primary_id}:{key}:*")
                value_field_names = [value_key.decode().split(":")[-1] for value_key in value_fields]
                if isinstance(value, int):
                    value_field_names = sorted([int(key) for key in value_field_names])[value:]
                elif isinstance(value, list):
                    value_field_names = [key for key in value_field_names if key in value]
                elif value != ALL_ITEMS:
                    value_field_names = list()
                context[key] = dict()
                for field in value_field_names:
                    raw_value = await self._redis.get(f"{self._DATA_TABLE}:{primary_id}:{key}:{field}")
                    context[key][field] = pickle.loads(raw_value) if raw_value is not None else None
        return context

    async def _write_ctx_val(self, field: Optional[str], payload: FieldDescriptor, nested: bool, primary_id: str):
        if nested:
            data, enforce = payload
            for key, value in data.items():
                current_data = await self._redis.get(f"{self._DATA_TABLE}:{primary_id}:{field}:{key}")
                if enforce or current_data is None:
                    raw_data = pickle.dumps(value)
                    await self._redis.set(f"{self._DATA_TABLE}:{primary_id}:{field}:{key}", raw_data)
        else:
            for key, (data, enforce) in payload.items():
                current_data = await self._redis.get(f"{self._DATA_TABLE}:{primary_id}:{key}")
                if enforce or current_data is None:
                    raw_data = pickle.dumps(data)
                    await self._redis.set(f"{self._DATA_TABLE}:{primary_id}:{key}", raw_data)
