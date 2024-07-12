import threading
from typing import Dict, List, Optional, Set, Tuple

from chatsky.context_storages.context_schema import ContextSchema, ExtraFields

from .database import DBContextStorage, cast_key_to_string, threadsafe_method


class MemoryContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` storing contexts in memory, wthout file backend.
    WARNING: it doesn't have `full_path`, `path` and `serializer` fields.

    :param context_schema: Context schema for this storage.
    """

    _CONTEXTS_TABLE = "contexts"
    _LOGS_TABLE = "logs"
    _VALUE_COLUMN = "value"
    _PACKED_COLUMN = "data"

    async def __init__(self, context_schema: Optional[ContextSchema] = None):
        self.__sync_init__(context_schema)

    def __sync_init__(self, context_schema: Optional[ContextSchema] = None):
        self._lock = threading.Lock()
        """Threading for methods that require single thread access."""
        self._insert_limit = False
        """Maximum number of items that can be inserted simultaneously, False if no such limit exists."""
        self.set_context_schema(context_schema)

        self.context_storage = dict()
        self.log_storage = dict()

    @threadsafe_method
    @cast_key_to_string()
    async def delete(self, key: str):
        for id in self.context_storage.keys():
            if self.context_storage[id][ExtraFields.storage_key.value] == key:
                self.context_storage[id][ExtraFields.active_ctx.value] = False

    @threadsafe_method
    @cast_key_to_string()
    async def contains(self, key: str) -> bool:
        return await self._get_last_ctx(key) is not None

    @threadsafe_method
    async def length(self) -> int:
        return len(
            {
                v[ExtraFields.storage_key.value]
                for v in self.context_storage.values()
                if v[ExtraFields.active_ctx.value]
            }
        )

    @threadsafe_method
    async def clear(self, prune_history: bool = False):
        if prune_history:
            self.context_storage.clear()
            self.log_storage.clear()
        else:
            for key in self.context_storage.keys():
                self.context_storage[key][ExtraFields.active_ctx.value] = False

    @threadsafe_method
    async def keys(self) -> Set[str]:
        return {
            ctx[ExtraFields.storage_key.value]
            for ctx in self.context_storage.values()
            if ctx[ExtraFields.active_ctx.value]
        }

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        """
        Get the last (active) context `_primary_id` for given storage key.

        :param storage_key: the key the context is associated with.
        :return: Context `_primary_id` or None if not found.
        """
        timed = sorted(
            self.context_storage.items(), key=lambda v: v[1][ExtraFields.updated_at.value], reverse=True
        )
        for key, value in timed:
            if value[ExtraFields.storage_key.value] == storage_key and value[ExtraFields.active_ctx.value]:
                return key
        return None

    async def _read_pac_ctx(self, storage_key: str) -> Tuple[Dict, Optional[str]]:
        primary_id = await self._get_last_ctx(storage_key)
        if primary_id is not None:
            return self.context_storage[primary_id][self._PACKED_COLUMN], primary_id
        else:
            return dict(), None

    async def _read_log_ctx(self, keys_limit: Optional[int], field_name: str, primary_id: str) -> Dict:
        key_set = [int(k) for k in self.log_storage[primary_id][field_name].keys()]
        key_set = [int(k) for k in sorted(key_set, reverse=True)]
        keys = key_set if keys_limit is None else key_set[:keys_limit]
        return {
            k: self.log_storage[primary_id][field_name][str(k)][self._VALUE_COLUMN]
            for k in keys
        }

    async def _write_pac_ctx(self, data: Dict, created: int, updated: int, storage_key: str, primary_id: str):
        self.context_storage[primary_id] = {
            ExtraFields.storage_key.value: storage_key,
            ExtraFields.active_ctx.value: True,
            self._PACKED_COLUMN: data,
            ExtraFields.created_at.value: created,
            ExtraFields.updated_at.value: updated,
        }

    async def _write_log_ctx(self, data: List[Tuple[str, int, Dict]], updated: int, primary_id: str):
        for field, key, value in data:
            self.log_storage.setdefault(primary_id, dict()).setdefault(field, dict()).setdefault(
                key,
                {
                    self._VALUE_COLUMN: value,
                    ExtraFields.updated_at.value: updated,
                },
            )
