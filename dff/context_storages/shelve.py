"""
Shelve
------
The Shelve module provides a shelve-based version of the :py:class:`.DBContextStorage` class.
This class is used to store and retrieve context data in a shelve format.
It allows the DFF to easily store and retrieve context data in a format that is efficient
for serialization and deserialization and can be easily used in python.

Shelve is a python library that allows to store and retrieve python objects.
It is efficient and fast, but it is not recommended to use it to transfer data across different languages
or platforms because it's not cross-language compatible.
It stores data in a dbm-style format in the file system, which is not as fast as the other serialization
libraries like pickle or JSON.
"""
from datetime import datetime
from pathlib import Path
from shelve import DbfilenameShelf
from typing import Any, Tuple, List, Dict, Optional

from .context_schema import ContextSchema, ExtraFields
from .database import DBContextStorage, cast_key_to_string
from .serializer import DefaultSerializer


class ShelveContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` with `shelve` as the driver.

    :param path: Target file URI. Example: `shelve://file.db`.
    """

    _CONTEXTS_TABLE = "contexts"
    _LOGS_TABLE = "logs"
    _VALUE_COLUMN = "value"
    _PACKED_COLUMN = "data"

    def __init__(self, path: str, context_schema: Optional[ContextSchema] = None, serializer: Any = DefaultSerializer()):
        DBContextStorage.__init__(self, path, context_schema, serializer)
        file_path = Path(self.path)
        self.context_db = DbfilenameShelf(str(file_path.with_stem(f"{file_path.stem}_{self._CONTEXTS_TABLE}").resolve()), writeback=True)
        self.log_db = DbfilenameShelf(str(file_path.with_stem(f"{file_path.stem}_{self._LOGS_TABLE}").resolve()), writeback=True)

    @cast_key_to_string()
    async def del_item_async(self, key: str):
        for id in self.context_db.keys():
            if self.context_db[id][ExtraFields.storage_key.value] == key:
                self.context_db[id][ExtraFields.active_ctx.value] = False

    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        return await self._get_last_ctx(key) is not None

    async def len_async(self) -> int:
        return len({v[ExtraFields.storage_key.value] for v in self.context_db.values() if v[ExtraFields.active_ctx.value]})

    async def clear_async(self):
        for key in self.context_db.keys():
            self.context_db[key][ExtraFields.active_ctx.value] = False

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        timed = sorted(self.context_db.items(), key=lambda v: v[1][ExtraFields.updated_at.value], reverse=True)
        for key, value in timed:
            if value[ExtraFields.storage_key.value] == storage_key and value[ExtraFields.active_ctx.value]:
                return key
        return None

    async def _read_pac_ctx(self, storage_key: str) -> Tuple[Dict, Optional[str]]:
        primary_id = await self._get_last_ctx(storage_key)
        if primary_id is not None:
            return self.serializer.loads(self.context_db[primary_id][self._PACKED_COLUMN]), primary_id
        else:
            return dict(), None

    async def _read_log_ctx(self, keys_limit: Optional[int], field_name: str, primary_id: str) -> Dict:
        key_set = [k for k in sorted(self.log_db[primary_id][field_name].keys(), reverse=True)]
        keys = key_set if keys_limit is None else key_set[:keys_limit]
        return {k: self.serializer.loads(self.log_db[primary_id][field_name][k][self._VALUE_COLUMN]) for k in keys}

    async def _write_pac_ctx(self, data: Dict, created: datetime, updated: datetime, storage_key: str, primary_id: str):
        self.context_db[primary_id] = {
            ExtraFields.storage_key.value: storage_key,
            ExtraFields.active_ctx.value: True,
            self._PACKED_COLUMN: self.serializer.dumps(data),
            ExtraFields.created_at.value: created,
            ExtraFields.updated_at.value: updated,
        }

    async def _write_log_ctx(self, data: List[Tuple[str, int, Dict]], updated: datetime, primary_id: str):
        for field, key, value in data:
            self.log_db.setdefault(primary_id, dict()).setdefault(field, dict()).setdefault(key, {
                self._VALUE_COLUMN: self.serializer.dumps(value),
                ExtraFields.updated_at.value: updated,
            })
