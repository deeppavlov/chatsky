"""
redis_connector
---------------------------
Provides the redis-based version of the :py:class:`~df_db_connector.db_connector.DBConnector`.
"""
import json

try:
    from redis import Redis

    redis_available = True
except ImportError:
    redis_available = False

from df_engine.core.context import Context

from .db_connector import DBConnector, threadsafe_method
from .protocol import get_protocol_install_suggestion


class RedisConnector(DBConnector):
    """
    Implements :py:class:`~df_db_connector.db_connector.DBConnector` with `redis` as the database backend.

    Parameters
    -----------

    path: str
        Database URI string. Example: redis://user:password@host:port
    """

    def __init__(self, path: str):
        super(RedisConnector, self).__init__(path)
        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        self._redis = Redis.from_url(self.full_path)

    @threadsafe_method
    def __contains__(self, key: str) -> bool:
        key = str(key)
        return self._redis.exists(key)

    @threadsafe_method
    def __setitem__(self, key: str, value: Context) -> None:
        key = str(key)
        value = value if isinstance(value, Context) else Context(value)
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
