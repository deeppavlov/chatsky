"""
JSON
----
The JSON module provides a json-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a JSON. It allows the DFF to easily
store and retrieve context data.
"""

import asyncio
from pathlib import Path
from base64 import encodebytes, decodebytes
from typing import Any, List, Set, Tuple, Dict, Optional

from pydantic import BaseModel

from .serializer import DefaultSerializer
from .context_schema import ContextSchema, ExtraFields
from .database import DBContextStorage, threadsafe_method, cast_key_to_string

try:
    from aiofiles import open
    from aiofiles.os import stat, makedirs
    from aiofiles.ospath import isfile

    json_available = True
except ImportError:
    json_available = False


class SerializableStorage(BaseModel, extra="allow"):
    pass


class StringSerializer:
    def __init__(self, serializer: Any):
        self._serializer = serializer

    def dumps(self, data: Any, _: Optional[Any] = None) -> str:
        return encodebytes(self._serializer.dumps(data)).decode("utf-8")

    def loads(self, data: str) -> Any:
        return self._serializer.loads(decodebytes(data.encode("utf-8")))


class JSONContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `json` as the storage format.

    :param path: Target file URI. Example: `json://file.json`.
    :param context_schema: Context schema for this storage.
    :param serializer: Serializer that will be used for serializing contexts.
    """

    _CONTEXTS_TABLE = "contexts"
    _LOGS_TABLE = "logs"
    _VALUE_COLUMN = "value"
    _PACKED_COLUMN = "data"

    def __init__(
        self, path: str, context_schema: Optional[ContextSchema] = None, serializer: Any = DefaultSerializer()
    ):
        DBContextStorage.__init__(self, path, context_schema, StringSerializer(serializer))
        self.context_schema.supports_async = False
        file_path = Path(self.path)
        context_file = file_path.with_name(f"{file_path.stem}_{self._CONTEXTS_TABLE}{file_path.suffix}")
        self.context_table = (context_file, SerializableStorage())
        log_file = file_path.with_name(f"{file_path.stem}_{self._LOGS_TABLE}{file_path.suffix}")
        self.log_table = (log_file, SerializableStorage())
        asyncio.run(asyncio.gather(self._load(self.context_table), self._load(self.log_table)))

    @threadsafe_method
    @cast_key_to_string()
    async def del_item_async(self, key: str):
        for id in self.context_table[1].model_extra.keys():
            if self.context_table[1].model_extra[id][ExtraFields.storage_key.value] == key:
                self.context_table[1].model_extra[id][ExtraFields.active_ctx.value] = False
        await self._save(self.context_table)

    @threadsafe_method
    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        self.context_table = await self._load(self.context_table)
        return await self._get_last_ctx(key) is not None

    @threadsafe_method
    async def len_async(self) -> int:
        self.context_table = await self._load(self.context_table)
        return len(
            {
                v[ExtraFields.storage_key.value]
                for v in self.context_table[1].model_extra.values()
                if v[ExtraFields.active_ctx.value]
            }
        )

    @threadsafe_method
    async def clear_async(self, prune_history: bool = False):
        if prune_history:
            self.context_table[1].model_extra.clear()
            self.log_table[1].model_extra.clear()
            await self._save(self.log_table)
        else:
            for key in self.context_table[1].model_extra.keys():
                self.context_table[1].model_extra[key][ExtraFields.active_ctx.value] = False
        await self._save(self.context_table)

    @threadsafe_method
    async def keys_async(self) -> Set[str]:
        self.context_table = await self._load(self.context_table)
        return {
            ctx[ExtraFields.storage_key.value]
            for ctx in self.context_table[1].model_extra.values()
            if ctx[ExtraFields.active_ctx.value]
        }

    async def _save(self, table: Tuple[Path, SerializableStorage]):
        """
        Flush internal storage to disk.

        :param table: tuple of path to save the storage and the storage itself.
        """
        await makedirs(table[0].parent, exist_ok=True)
        async with open(table[0], "w+", encoding="utf-8") as file_stream:
            await file_stream.write(table[1].model_dump_json())

    async def _load(self, table: Tuple[Path, SerializableStorage]) -> Tuple[Path, SerializableStorage]:
        """
        Load internal storage to disk.

        :param table: tuple of path to save the storage and the storage itself.
        """
        if not await isfile(table[0]) or (await stat(table[0])).st_size == 0:
            storage = SerializableStorage()
            await self._save((table[0], storage))
        else:
            async with open(table[0], "r", encoding="utf-8") as file_stream:
                storage = SerializableStorage.model_validate_json(await file_stream.read())
        return table[0], storage

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        """
        Get the last (active) context `_primary_id` for given storage key.

        :param storage_key: the key the context is associated with.
        :return: Context `_primary_id` or None if not found.
        """
        timed = sorted(
            self.context_table[1].model_extra.items(), key=lambda v: v[1][ExtraFields.updated_at.value], reverse=True
        )
        for key, value in timed:
            if value[ExtraFields.storage_key.value] == storage_key and value[ExtraFields.active_ctx.value]:
                return key
        return None

    async def _read_pac_ctx(self, storage_key: str) -> Tuple[Dict, Optional[str]]:
        self.context_table = await self._load(self.context_table)
        primary_id = await self._get_last_ctx(storage_key)
        if primary_id is not None:
            return self.serializer.loads(self.context_table[1].model_extra[primary_id][self._PACKED_COLUMN]), primary_id
        else:
            return dict(), None

    async def _read_log_ctx(self, keys_limit: Optional[int], field_name: str, primary_id: str) -> Dict:
        self.log_table = await self._load(self.log_table)
        key_set = [int(k) for k in self.log_table[1].model_extra[primary_id][field_name].keys()]
        key_set = [int(k) for k in sorted(key_set, reverse=True)]
        keys = key_set if keys_limit is None else key_set[:keys_limit]
        return {
            k: self.serializer.loads(self.log_table[1].model_extra[primary_id][field_name][str(k)][self._VALUE_COLUMN])
            for k in keys
        }

    async def _write_pac_ctx(self, data: Dict, created: int, updated: int, storage_key: str, primary_id: str):
        self.context_table[1].model_extra[primary_id] = {
            ExtraFields.storage_key.value: storage_key,
            ExtraFields.active_ctx.value: True,
            self._PACKED_COLUMN: self.serializer.dumps(data),
            ExtraFields.created_at.value: created,
            ExtraFields.updated_at.value: updated,
        }
        await self._save(self.context_table)

    async def _write_log_ctx(self, data: List[Tuple[str, int, Dict]], updated: int, primary_id: str):
        for field, key, value in data:
            self.log_table[1].model_extra.setdefault(primary_id, dict()).setdefault(field, dict()).setdefault(
                key,
                {
                    self._VALUE_COLUMN: self.serializer.dumps(value),
                    ExtraFields.updated_at.value: updated,
                },
            )
        await self._save(self.log_table)
