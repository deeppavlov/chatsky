"""
Redis
-----
The Redis module provides a Redis-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a Redis.
It allows Chatsky to easily store and retrieve context data in a format that is highly scalable
and easy to work with.

Redis is an open-source, in-memory data structure store that is known for its
high performance and scalability. It stores data in key-value pairs and supports a variety of data
structures such as strings, hashes, lists, sets, and more.
Additionally, Redis can be used as a cache, message broker, and database, making it a versatile
and powerful choice for data storage and management.
"""

from asyncio import gather
from typing import Callable, Hashable, List, Dict, Set, Tuple, Optional

try:
    from redis.asyncio import Redis

    redis_available = True
except ImportError:
    redis_available = False

from .database import DBContextStorage, FieldConfig
from .protocol import get_protocol_install_suggestion


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

    is_asynchronous = True

    def __init__(
        self,
        path: str,
        rewrite_existing: bool = False,
        configuration: Optional[Dict[str, FieldConfig]] = None,
        key_prefix: str = "chatsky_keys",
    ):
        DBContextStorage.__init__(self, path, rewrite_existing, configuration)

        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        if not bool(key_prefix):
            raise ValueError("`key_prefix` parameter shouldn't be empty")
        self._redis = Redis.from_url(self.full_path)

        self._prefix = key_prefix
        self._main_key = f"{key_prefix}:{self._main_table_name}"
        self._turns_key = f"{key_prefix}:{self._turns_table_name}"
        self._misc_key = f"{key_prefix}:{self._misc_table_name}"

    @staticmethod
    def _keys_to_bytes(keys: List[Hashable]) -> List[bytes]:
        return [str(f).encode("utf-8") for f in keys]

    @staticmethod
    def _bytes_to_keys_converter(constructor: Callable[[str], Hashable] = str) -> Callable[[List[bytes]], List[Hashable]]:
        return lambda k: [constructor(f.decode("utf-8")) for f in k]

    # TODO: this method (and similar) repeat often. Optimize?
    def _get_config_for_field(self, field_name: str, ctx_id: str) -> Tuple[str, Callable[[List[bytes]], List[Hashable]], FieldConfig]:
        if field_name == self.labels_config.name:
            return f"{self._turns_key}:{ctx_id}:{field_name}", self._bytes_to_keys_converter(int), self.labels_config
        elif field_name == self.requests_config.name:
            return f"{self._turns_key}:{ctx_id}:{field_name}", self._bytes_to_keys_converter(int), self.requests_config
        elif field_name == self.responses_config.name:
            return f"{self._turns_key}:{ctx_id}:{field_name}", self._bytes_to_keys_converter(int), self.responses_config
        elif field_name == self.misc_config.name:
            return f"{self._misc_key}:{ctx_id}", self._bytes_to_keys_converter(), self.misc_config
        else:
            raise ValueError(f"Unknown field name: {field_name}!")

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes]]:
        if await self._redis.exists(f"{self._main_key}:{ctx_id}"):
            cti, ca, ua, fd = await gather(
                self._redis.hget(f"{self._main_key}:{ctx_id}", self._current_turn_id_column_name),
                self._redis.hget(f"{self._main_key}:{ctx_id}", self._created_at_column_name),
                self._redis.hget(f"{self._main_key}:{ctx_id}", self._updated_at_column_name),
                self._redis.hget(f"{self._main_key}:{ctx_id}", self._framework_data_column_name)
            )
            return (int(cti), int(ca), int(ua), fd)
        else:
            return None

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, fw_data: bytes) -> None:
        await gather(
            self._redis.hset(f"{self._main_key}:{ctx_id}", self._current_turn_id_column_name, str(turn_id)),
            self._redis.hset(f"{self._main_key}:{ctx_id}", self._created_at_column_name, str(crt_at)),
            self._redis.hset(f"{self._main_key}:{ctx_id}", self._updated_at_column_name, str(upd_at)),
            self._redis.hset(f"{self._main_key}:{ctx_id}", self._framework_data_column_name, fw_data)
        )

    async def delete_context(self, ctx_id: str) -> None:
        keys = await self._redis.keys(f"{self._prefix}:*:{ctx_id}*")
        if len(keys) > 0:
            await self._redis.delete(*keys)

    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[Hashable, bytes]]:
        field_key, field_converter, field_config = self._get_config_for_field(field_name, ctx_id)
        keys = await self._redis.hkeys(field_key)
        if field_key.startswith(self._turns_key):
            keys = sorted(keys, key=lambda k: int(k), reverse=True)
        if isinstance(field_config.subscript, int):
            keys = keys[:field_config.subscript]
        elif isinstance(field_config.subscript, Set):
            keys = [k for k in keys if k in self._keys_to_bytes(field_config.subscript)]
        values = await gather(*[self._redis.hget(field_key, k) for k in keys])
        return [(k, v) for k, v in zip(field_converter(keys), values)]

    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[Hashable]:
        field_key, field_converter, _ = self._get_config_for_field(field_name, ctx_id)
        return field_converter(await self._redis.hkeys(field_key))

    async def load_field_items(self, ctx_id: str, field_name: str, keys: List[Hashable]) -> List[Tuple[Hashable, bytes]]:
        field_key, field_converter, _ = self._get_config_for_field(field_name, ctx_id)
        load = [k for k in await self._redis.hkeys(field_key) if k in self._keys_to_bytes(keys)]
        values = await gather(*[self._redis.hget(field_key, k) for k in load])
        return [(k, v) for k, v in zip(field_converter(load), values)]

    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[Hashable, bytes]]) -> None:
        field_key, _, _ = self._get_config_for_field(field_name, ctx_id)
        await gather(*[self._redis.hset(field_key, str(k), v) for k, v in items])

    async def delete_field_keys(self, ctx_id: str, field_name: str, keys: List[Hashable]) -> None:
        field_key, _, _ = self._get_config_for_field(field_name, ctx_id)
        match = [k for k in await self._redis.hkeys(field_key) if k in self._keys_to_bytes(keys)]
        if len(match) > 0:
            await self._redis.hdel(field_key, *match)

    async def clear_all(self) -> None:
        keys = await self._redis.keys(f"{self._prefix}:*")
        if len(keys) > 0:
            await self._redis.delete(*keys)
