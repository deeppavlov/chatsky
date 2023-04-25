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
from typing import Hashable, List, Dict, Any, Union, Tuple, Optional

try:
    from aioredis import Redis

    redis_available = True
except ImportError:
    redis_available = False
    Redis = None

from dff.script import Context

from .database import DBContextStorage, threadsafe_method, auto_stringify_hashable_key
from .update_scheme import ValueField
from .protocol import get_protocol_install_suggestion


class RedisContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `redis` as the database backend.

    :param path: Database URI string. Example: `redis://user:password@host:port`.
    """

    _CONTEXTS_KEY = "all_contexts"
    _VALUE_NONE = b""

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        self._redis = Redis.from_url(self.full_path)

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def get_item_async(self, key: Union[Hashable, str]) -> Context:
        fields, int_id = await self._read_keys(key)
        if int_id is None:
            raise KeyError(f"No entry for key {key}.")
        context, hashes = await self.update_scheme.read_context(fields, self._read_ctx, key, int_id)
        self.hash_storage[key] = hashes
        return context

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def set_item_async(self, key: Union[Hashable, str], value: Context):
        fields, int_id = await self._read_keys(key)
        value_hash = self.hash_storage.get(key, None)
        await self.update_scheme.write_context(value, value_hash, fields, self._write_ctx, key)
        if int_id != value.id and int_id is None:
            await self._redis.rpush(self._CONTEXTS_KEY, key)

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def del_item_async(self, key: Union[Hashable, str]):
        await self._redis.rpush(key, self._VALUE_NONE)
        await self._redis.lrem(self._CONTEXTS_KEY, 0, key)

    @threadsafe_method
    @auto_stringify_hashable_key()
    async def contains_async(self, key: Union[Hashable, str]) -> bool:
        if bool(await self._redis.exists(key)):
            value = await self._redis.rpop(key)
            await self._redis.rpush(key, value)
            return self._check_none(value) is not None
        else:
            return False

    @threadsafe_method
    async def len_async(self) -> int:
        return int(await self._redis.llen(self._CONTEXTS_KEY))

    @threadsafe_method
    async def clear_async(self):
        while int(await self._redis.llen(self._CONTEXTS_KEY)) > 0:
            value = await self._redis.rpop(self._CONTEXTS_KEY)
            await self._redis.rpush(value, self._VALUE_NONE)

    @classmethod
    def _check_none(cls, value: Any) -> Any:
        return None if value == cls._VALUE_NONE else value

    async def _read_keys(self, ext_id: str) -> Tuple[Dict[str, List[str]], Optional[str]]:
        key_dict = dict()
        int_id = self._check_none(await self._redis.rpop(ext_id))
        if int_id is None:
            return key_dict, None
        else:
            int_id = int_id.decode()
        await self._redis.rpush(ext_id, int_id)
        for field in [
            field for field, field_props in dict(self.update_scheme).items() if not isinstance(field_props, ValueField)
        ]:
            for key in await self._redis.keys(f"{ext_id}:{int_id}:{field}:*"):
                res = key.decode().split(":")[-1]
                if field not in key_dict:
                    key_dict[field] = list()
                key_dict[field] += [int(res) if res.isdigit() else res]
        return key_dict, int_id

    async def _read_ctx(self, outlook: Dict[str, Union[bool, Dict[Hashable, bool]]], int_id: str, ext_id: str) -> Dict:
        result_dict = dict()
        for field in [field for field, value in outlook.items() if isinstance(value, dict) and len(value) > 0]:
            for key in [key for key, value in outlook[field].items() if value]:
                value = await self._redis.get(f"{ext_id}:{int_id}:{field}:{key}")
                if value is not None:
                    if field not in result_dict:
                        result_dict[field] = dict()
                    result_dict[field][key] = pickle.loads(value)
        for field in [field for field, value in outlook.items() if isinstance(value, bool) and value]:
            value = await self._redis.get(f"{ext_id}:{int_id}:{field}")
            if value is not None:
                result_dict[field] = pickle.loads(value)
        return result_dict

    async def _write_ctx(self, data: Dict[str, Any], int_id: str, ext_id: str):
        for holder in data.keys():
            if isinstance(getattr(self.update_scheme, holder), ValueField):
                await self._redis.set(f"{ext_id}:{int_id}:{holder}", pickle.dumps(data.get(holder, None)))
            else:
                for key, value in data.get(holder, dict()).items():
                    await self._redis.set(f"{ext_id}:{int_id}:{holder}:{key}", pickle.dumps(value))
        await self._redis.rpush(ext_id, int_id)
