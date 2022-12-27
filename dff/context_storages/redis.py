"""
redis
---------------------------
Provides the redis-based version of the :py:class:`.DBContextStorage`.
"""
import json
from typing import Any

try:
    from aioredis import Redis

    redis_available = True
except ImportError:
    redis_available = False

from dff.script import Context

from .database import DBContextStorage, threadsafe_method
from .protocol import get_protocol_install_suggestion


class RedisContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `redis` as the database backend.

    Parameters
    -----------

    path: str
        Database URI string. Example: redis://user:password@host:port
    """

    def __init__(self, path: str):
        super(RedisContextStorage, self).__init__(path)
        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        self._redis = Redis.from_url(self.full_path)

    @threadsafe_method
    async def contains(self, key: str) -> bool:
        key = str(key)
        return bool(await self._redis.exists(key))

    @threadsafe_method
    async def setitem(self, key: Any, value: Context):
        key = str(key)
        value = value if isinstance(value, Context) else Context.cast(value)
        await self._redis.set(key, value.json())

    @threadsafe_method
    async def getitem(self, key: Any) -> Context:
        key = str(key)
        result = await self._redis.get(key)
        if result:
            result_dict = json.loads(result.decode("utf-8"))
            return Context.cast(result_dict)
        raise KeyError(f"No entry for key {key}.")

    @threadsafe_method
    async def delitem(self, key: str) -> None:
        key = str(key)
        await self._redis.delete(key)

    @threadsafe_method
    async def len(self) -> int:
        return await self._redis.dbsize()

    @threadsafe_method
    async def clear_async(self) -> None:
        await self._redis.flushdb()
