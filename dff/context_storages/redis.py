"""
Redis
-----
Provides the redis-based version of the :py:class:`.DBContextStorage`.
"""
import json

try:
    from redis import Redis

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
    :type path: str
    """

    def __init__(self, path: str):
        super(RedisContextStorage, self).__init__(path)
        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        self._redis = Redis.from_url(self.full_path)

    @threadsafe_method
    def __contains__(self, key: str) -> bool:
        key = str(key)
        return bool(self._redis.exists(key))

    @threadsafe_method
    def __setitem__(self, key: str, value: Context) -> None:
        key = str(key)
        value = value if isinstance(value, Context) else Context.cast(value)
        self._redis.set(key, value.json())

    @threadsafe_method
    def __getitem__(self, key: str) -> Context:
        key = str(key)
        result = self._redis.get(key)
        if result:
            result_dict = json.loads(result.decode("utf-8"))
            return Context.cast(result_dict)
        raise KeyError(f"No entry for key {key}.")

    @threadsafe_method
    def __delitem__(self, key: str) -> None:
        key = str(key)
        self._redis.delete(key)

    @threadsafe_method
    def __len__(self) -> int:
        return self._redis.dbsize()

    @threadsafe_method
    def clear(self) -> None:
        self._redis.flushdb()
