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
import json
from typing import Hashable

try:
    from redis.asyncio import Redis

    redis_available = True
except ImportError:
    redis_available = False

from dff.script import Context

from .database import DBContextStorage, threadsafe_method
from .protocol import get_protocol_install_suggestion


class RedisContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `redis` as the database backend.

    :param path: Database URI string. Example: `redis://user:password@host:port`.
    """

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        self._redis = Redis.from_url(self.full_path)

    @threadsafe_method
    async def contains_async(self, key: Hashable) -> bool:
        return bool(await self._redis.exists(str(key)))

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        value = value if isinstance(value, Context) else Context.cast(value)
        await self._redis.set(str(key), value.model_dump_json())

    @threadsafe_method
    async def get_item_async(self, key: Hashable) -> Context:
        result = await self._redis.get(str(key))
        if result:
            result_dict = json.loads(result.decode("utf-8"))
            return Context.cast(result_dict)
        raise KeyError(f"No entry for key {key}.")

    @threadsafe_method
    async def del_item_async(self, key: Hashable):
        await self._redis.delete(str(key))

    @threadsafe_method
    async def len_async(self) -> int:
        return await self._redis.dbsize()

    @threadsafe_method
    async def clear_async(self):
        await self._redis.flushdb()
