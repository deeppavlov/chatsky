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

from typing import Any, List, Dict, Set, Tuple, Optional

try:
    from redis.asyncio import Redis

    redis_available = True
except ImportError:
    redis_available = False

from .database import DBContextStorage, threadsafe_method, cast_key_to_string
from .context_schema import ContextSchema, ExtraFields
from .protocol import get_protocol_install_suggestion
from .serializer import DefaultSerializer


class RedisContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `redis` as the database backend.

    The relations between primary identifiers and active context storage keys are stored
    as a redis hash ("KEY_PREFIX:index:general").
    The keys of active contexts are stored as redis sets ("KEY_PREFIX:index:subindex:PRIMARY_ID").

    That's how CONTEXT table fields are stored:
    `"KEY_PREFIX:contexts:PRIMARY_ID:FIELD": "DATA"`
    That's how LOGS table fields are stored:
    `"KEY_PREFIX:logs:PRIMARY_ID:FIELD": "DATA"`

    :param path: Database URI string. Example: `redis://user:password@host:port`.
    :param context_schema: Context schema for this storage.
    :param serializer: Serializer that will be used for serializing contexts.
    :param key_prefix: "namespace" prefix for all keys, should be set for efficient clearing of all data.
    """

    _INDEX_TABLE = "index"
    _CONTEXTS_TABLE = "contexts"
    _LOGS_TABLE = "logs"
    _GENERAL_INDEX = "general"
    _LOGS_INDEX = "subindex"

    def __init__(
        self,
        path: str,
        context_schema: Optional[ContextSchema] = None,
        serializer: Any = DefaultSerializer(),
        key_prefix: str = "dff_keys",
    ):
        DBContextStorage.__init__(self, path, context_schema, serializer)
        self.context_schema.supports_async = True

        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        if not bool(key_prefix):
            raise ValueError("`key_prefix` parameter shouldn't be empty")

        self._prefix = key_prefix
        self._redis = Redis.from_url(self.full_path)
        self._index_key = f"{key_prefix}:{self._INDEX_TABLE}"
        self._context_key = f"{key_prefix}:{self._CONTEXTS_TABLE}"
        self._logs_key = f"{key_prefix}:{self._LOGS_TABLE}"

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: str):
        await self._redis.hdel(f"{self._index_key}:{self._GENERAL_INDEX}", key)

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        return await self._redis.hexists(f"{self._index_key}:{self._GENERAL_INDEX}", key)

    @threadsafe_method
    async def len_async(self) -> int:
        return len(await self._redis.hkeys(f"{self._index_key}:{self._GENERAL_INDEX}"))

    @threadsafe_method
    async def clear_async(self, prune_history: bool = False):
        if prune_history:
            keys = await self._redis.keys(f"{self._prefix}:*")
            if len(keys) > 0:
                await self._redis.delete(*keys)
        else:
            await self._redis.delete(f"{self._index_key}:{self._GENERAL_INDEX}")

    @threadsafe_method
    async def keys_async(self) -> Set[str]:
        keys = await self._redis.hkeys(f"{self._index_key}:{self._GENERAL_INDEX}")
        return {key.decode() for key in keys}

    async def _read_pac_ctx(self, storage_key: str) -> Tuple[Dict, Optional[str]]:
        last_primary_id = await self._redis.hget(f"{self._index_key}:{self._GENERAL_INDEX}", storage_key)
        if last_primary_id is not None:
            primary = last_primary_id.decode()
            packed = await self._redis.get(f"{self._context_key}:{primary}")
            return self.serializer.loads(packed), primary
        else:
            return dict(), None

    async def _read_log_ctx(self, keys_limit: Optional[int], field_name: str, primary_id: str) -> Dict:
        all_keys = await self._redis.smembers(f"{self._index_key}:{self._LOGS_INDEX}:{primary_id}:{field_name}")
        keys_limit = keys_limit if keys_limit is not None else len(all_keys)
        read_keys = sorted([int(key) for key in all_keys], reverse=True)[:keys_limit]
        return {
            key: self.serializer.loads(await self._redis.get(f"{self._logs_key}:{primary_id}:{field_name}:{key}"))
            for key in read_keys
        }

    async def _write_pac_ctx(self, data: Dict, created: int, updated: int, storage_key: str, primary_id: str):
        await self._redis.hset(f"{self._index_key}:{self._GENERAL_INDEX}", storage_key, primary_id)
        await self._redis.set(f"{self._context_key}:{primary_id}", self.serializer.dumps(data))
        await self._redis.set(
            f"{self._context_key}:{primary_id}:{ExtraFields.created_at.value}", self.serializer.dumps(created)
        )
        await self._redis.set(
            f"{self._context_key}:{primary_id}:{ExtraFields.updated_at.value}", self.serializer.dumps(updated)
        )

    async def _write_log_ctx(self, data: List[Tuple[str, int, Dict]], updated: int, primary_id: str):
        for field, key, value in data:
            await self._redis.sadd(f"{self._index_key}:{self._LOGS_INDEX}:{primary_id}:{field}", str(key))
            await self._redis.set(f"{self._logs_key}:{primary_id}:{field}:{key}", self.serializer.dumps(value))
            await self._redis.set(
                f"{self._logs_key}:{primary_id}:{field}:{key}:{ExtraFields.updated_at.value}",
                self.serializer.dumps(updated),
            )
