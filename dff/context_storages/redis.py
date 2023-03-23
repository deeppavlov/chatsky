"""
Redis
-----
The Redis module provides a Redis-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a Redis.
It allows the `DFF` to easily store and retrieve context data in a format that is highly scalable
and easy to work with.

Redis is an open-source, in-memory data structure store that is known for its
high performance and scalability. It stores data in key-value pairs and supports a variety of data
structures such as strings, hashes, lists, sets, and more.
Additionally, Redis can be used as a cache, message broker, and database, making it a versatile
and powerful choice for data storage and management.
"""
import pickle
from typing import Hashable, Optional, List, Dict, Any

try:
    from aioredis import Redis

    redis_available = True
except ImportError:
    redis_available = False

from dff.script import Context

from .database import DBContextStorage, threadsafe_method
from .protocol import get_protocol_install_suggestion
from .update_scheme import default_update_scheme, UpdateScheme, FieldType


class RedisContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `redis` as the database backend.

    :param path: Database URI string. Example: `redis://user:password@host:port`.
    :type path: str
    """

    _TOTAL_CONTEXT_COUNT_KEY = "total_contexts"

    def __init__(self, path: str):
        DBContextStorage.__init__(self, path)
        if not redis_available:
            install_suggestion = get_protocol_install_suggestion("redis")
            raise ImportError("`redis` package is missing.\n" + install_suggestion)
        self._redis = Redis.from_url(self.full_path)

    @threadsafe_method
    async def contains_async(self, key: Hashable) -> bool:
        return bool(await self._redis.exists(str(key)))

    async def _write_list(self, field_name: str, data: Dict[int, Any], outlook_list: Optional[List[int]], outlook_slice: Optional[List[int]], int_id: int, ext_id: int):
        if outlook_list is not None:
            update_list = UpdateScheme.get_outlook_list(data.keys(), outlook_list)
        else:
            update_list = UpdateScheme.get_outlook_slice(data.keys(), outlook_slice)
        for update in update_list:
            await self._redis.set(f"{ext_id}:{int_id}:{field_name}:{update}", pickle.dumps(data[update]))

    async def _write_dict(self, field_name: str, data: Dict[Hashable, Any], outlook: Optional[List[int]], int_id: int, ext_id: int):
        outlook = data.keys() if UpdateScheme.ALL_ITEMS in outlook else outlook
        for value in outlook:
            await self._redis.set(f"{ext_id}:{int_id}:{field_name}:{value}", pickle.dumps(data[value]))

    async def _write_value(self, data: Any, field_name: str, int_id: int, ext_id: int):
        return await self._redis.set(f"{ext_id}:{int_id}:{field_name}", pickle.dumps(data))

    @threadsafe_method
    async def set_item_async(self, key: Hashable, value: Context):
        key = str(key)
        await default_update_scheme.process_fields_write(value, {
            FieldType.LIST: self._write_list,
            FieldType.DICT: self._write_dict,
            FieldType.VALUE: self._write_value
        }, value.id, key)
        last_id = await self._redis.rpop(key)
        if last_id is None or last_id != str(value.id):
            if last_id is not None:
                await self._redis.rpush(key, last_id)
            else:
                await self._redis.incr(RedisContextStorage._TOTAL_CONTEXT_COUNT_KEY)
            await self._redis.rpush(key, str(value.id))

    async def _read_fields(self, field_name: str, int_id: int, ext_id: int):
        return [key.split(":")[-1] for key in self._redis.keys(f"{ext_id}:{int_id}:{field_name}:*")]

    async def _read_list(self, field_name: str, outlook_list: Optional[List[int]], outlook_slice: Optional[List[int]], int_id: int, ext_id: int) -> Dict[int, Any]:
        list_keys = [key.split(":")[-1] for key in self._redis.keys(f"{ext_id}:{int_id}:{field_name}:*")]
        if outlook_list is not None:
            update_list = UpdateScheme.get_outlook_list(list_keys, outlook_list)
        else:
            update_list = UpdateScheme.get_outlook_slice(list_keys, outlook_slice)
        result = dict()
        for index in update_list:
            value = await self._redis.get(f"{ext_id}:{int_id}:{field_name}:{index}")
            result[index] = pickle.loads(value) if value is not None else None
        return result

    async def _read_dict(self, field_name: str, outlook: Optional[List[int]], int_id: int, ext_id: int) -> Dict[Hashable, Any]:
        dict_keys = [key.split(":")[-1] for key in self._redis.keys(f"{ext_id}:{int_id}:{field_name}:*")]
        outlook = dict_keys if UpdateScheme.ALL_ITEMS in outlook else outlook
        result = dict()
        for key in outlook:
            value = await self._redis.get(f"{ext_id}:{int_id}:{field_name}:{key}")
            result[key] = pickle.loads(value) if value is not None else None
        return result

    async def _read_value(self, field_name: str, int_id: int, ext_id: int) -> Any:
        value = await self._redis.get(f"{ext_id}:{int_id}:{field_name}")
        return pickle.loads(value) if value is not None else None

    @threadsafe_method
    async def get_item_async(self, key: Hashable) -> Context:
        key = str(key)
        last_id = await self._redis.rpop(key)
        if last_id is None:
            raise KeyError(f"No entry for key {key}.")
        return await default_update_scheme.process_fields_read({
            FieldType.LIST: self._read_list,
            FieldType.DICT: self._read_dict,
            FieldType.VALUE: self._read_value
        }, self._read_fields, last_id, key)

    @threadsafe_method
    async def del_item_async(self, key: Hashable):
        for key in await self._redis.keys(f"{str(key)}:*"):
            await self._redis.delete(key)
        await self._redis.decr(RedisContextStorage._TOTAL_CONTEXT_COUNT_KEY)

    @threadsafe_method
    async def len_async(self) -> int:
        return int(await self._redis.get(RedisContextStorage._TOTAL_CONTEXT_COUNT_KEY))

    @threadsafe_method
    async def clear_async(self):
        await self._redis.flushdb()
        await self._redis.set(RedisContextStorage._TOTAL_CONTEXT_COUNT_KEY, 0)
