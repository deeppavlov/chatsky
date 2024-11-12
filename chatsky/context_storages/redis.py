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
from typing import Any, List, Dict, Set, Tuple, Optional, Union

try:
    from redis.asyncio import Redis

    redis_available = True
except ImportError:
    redis_available = False

from .database import ContextIdFilter, DBContextStorage, _SUBSCRIPT_DICT
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

    def __init__(
        self,
        path: str,
        rewrite_existing: bool = False,
        configuration: Optional[_SUBSCRIPT_DICT] = None,
        key_prefix: str = "chatsky_keys",
    ):
        DBContextStorage.__init__(self, path, rewrite_existing, configuration)

        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        if not bool(key_prefix):
            raise ValueError("`key_prefix` parameter shouldn't be empty")
        self.database = Redis.from_url(self.full_path)

        self._prefix = key_prefix
        self._main_key = f"{key_prefix}:{self._main_table_name}"
        self._turns_key = f"{key_prefix}:{self._turns_table_name}"

    @staticmethod
    def _keys_to_bytes(keys: List[int]) -> List[bytes]:
        return [str(f).encode("utf-8") for f in keys]

    @staticmethod
    def _bytes_to_keys(keys: List[bytes]) -> List[int]:
        return [int(f.decode("utf-8")) for f in keys]

    @DBContextStorage._convert_id_filter
    async def get_context_ids(self, filter: Union[ContextIdFilter, Dict[str, Any]]) -> Set[str]:
        context_ids = [k.decode("utf-8") for k in await self.database.keys(f"{self._main_key}:*")]
        context_upd = [int(await self.database.hget(f"{self._main_key}:{k}", self._updated_at_column_name)) for k in context_ids]
        partial_contexts = {k: (None, None, ua, None, None) for k, ua in zip(context_ids, context_upd)}
        return filter.filter_keys(partial_contexts)

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes, bytes]]:
        if await self.database.exists(f"{self._main_key}:{ctx_id}"):
            cti, ca, ua, msc, fd = await gather(
                self.database.hget(f"{self._main_key}:{ctx_id}", self._current_turn_id_column_name),
                self.database.hget(f"{self._main_key}:{ctx_id}", self._created_at_column_name),
                self.database.hget(f"{self._main_key}:{ctx_id}", self._updated_at_column_name),
                self.database.hget(f"{self._main_key}:{ctx_id}", self._misc_column_name),
                self.database.hget(f"{self._main_key}:{ctx_id}", self._framework_data_column_name)
            )
            return (int(cti), int(ca), int(ua), msc, fd)
        else:
            return None

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, misc: bytes, fw_data: bytes) -> None:
        await gather(
            self.database.hset(f"{self._main_key}:{ctx_id}", self._current_turn_id_column_name, str(turn_id)),
            self.database.hset(f"{self._main_key}:{ctx_id}", self._created_at_column_name, str(crt_at)),
            self.database.hset(f"{self._main_key}:{ctx_id}", self._updated_at_column_name, str(upd_at)),
            self.database.hset(f"{self._main_key}:{ctx_id}", self._misc_column_name, misc),
            self.database.hset(f"{self._main_key}:{ctx_id}", self._framework_data_column_name, fw_data)
        )

    async def delete_context(self, ctx_id: str) -> None:
        keys = await self.database.keys(f"{self._prefix}:*:{ctx_id}*")
        if len(keys) > 0:
            await self.database.delete(*keys)

    @DBContextStorage._verify_field_name
    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        field_key = f"{self._turns_key}:{ctx_id}:{field_name}"
        keys = sorted(await self.database.hkeys(field_key), key=lambda k: int(k), reverse=True)
        if isinstance(self._subscripts[field_name], int):
            keys = keys[:self._subscripts[field_name]]
        elif isinstance(self._subscripts[field_name], Set):
            keys = [k for k in keys if k in self._keys_to_bytes(self._subscripts[field_name])]
        values = await gather(*[self.database.hget(field_key, k) for k in keys])
        return [(k, v) for k, v in zip(self._bytes_to_keys(keys), values)]

    @DBContextStorage._verify_field_name
    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[int]:
        return self._bytes_to_keys(await self.database.hkeys(f"{self._turns_key}:{ctx_id}:{field_name}"))

    @DBContextStorage._verify_field_name
    async def load_field_items(self, ctx_id: str, field_name: str, keys: List[int]) -> List[Tuple[int, bytes]]:
        field_key = f"{self._turns_key}:{ctx_id}:{field_name}"
        load = [k for k in await self.database.hkeys(field_key) if k in self._keys_to_bytes(keys)]
        values = await gather(*[self.database.hget(field_key, k) for k in load])
        return [(k, v) for k, v in zip(self._bytes_to_keys(load), values)]

    @DBContextStorage._verify_field_name
    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[int, bytes]]) -> None:
        await gather(*[self.database.hset(f"{self._turns_key}:{ctx_id}:{field_name}", str(k), v) for k, v in items])

    @DBContextStorage._verify_field_name
    async def delete_field_keys(self, ctx_id: str, field_name: str, keys: List[int]) -> None:
        field_key = f"{self._turns_key}:{ctx_id}:{field_name}"
        match = [k for k in await self.database.hkeys(field_key) if k in self._keys_to_bytes(keys)]
        if len(match) > 0:
            await self.database.hdel(field_key, *match)

    async def clear_all(self) -> None:
        keys = await self.database.keys(f"{self._prefix}:*")
        if len(keys) > 0:
            await self.database.delete(*keys)
