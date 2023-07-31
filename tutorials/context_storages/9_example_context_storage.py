# %% [markdown]
"""
# 9. Custom context storage

In this tutorial, let's learn more about internal structure of context storage by writing custom
"in-memory" context storage, based on few python dictionaries.
"""


# %%
from datetime import datetime
from typing import Any, Set, Tuple, List, Dict, Optional

from dff.context_storages.context_schema import ContextSchema, ExtraFields
from dff.context_storages.database import DBContextStorage, cast_key_to_string
from dff.context_storages.serializer import DefaultSerializer

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import TOY_SCRIPT_ARGS, HAPPY_PATH


# %%
class MemoryContextStorage(DBContextStorage):
    _VALUE_COLUMN = "value"
    _PACKED_COLUMN = "data"

    def __init__(self, context_schema: Optional[ContextSchema] = None, serializer: Any = DefaultSerializer()):
        DBContextStorage.__init__(self, str(), context_schema, serializer)
        self.context_schema.supports_async = True
        self.context_dict = dict()
        self.log_dict = dict()

    @cast_key_to_string()
    async def del_item_async(self, key: str):
        for id in self.context_dict.keys():
            if self.context_dict[id][ExtraFields.storage_key.value] == key:
                self.context_dict[id][ExtraFields.active_ctx.value] = False

    @cast_key_to_string()
    async def contains_async(self, key: str) -> bool:
        return await self._get_last_ctx(key) is not None

    async def len_async(self) -> int:
        return len({v[ExtraFields.storage_key.value] for v in self.context_dict.values() if v[ExtraFields.active_ctx.value]})

    async def clear_async(self, prune_history: bool = False):
        if prune_history:
            self.context_dict.clear()
            self.log_dict.clear()
        else:
            for key in self.context_dict.keys():
                self.context_dict[key][ExtraFields.active_ctx.value] = False

    async def keys_async(self) -> Set[str]:
        return {ctx[ExtraFields.storage_key.value] for ctx in self.context_dict.values() if ctx[ExtraFields.active_ctx.value]}

    async def _get_last_ctx(self, storage_key: str) -> Optional[str]:
        timed = sorted(self.context_dict.items(), key=lambda v: v[1][ExtraFields.updated_at.value], reverse=True)
        for key, value in timed:
            if value[ExtraFields.storage_key.value] == storage_key and value[ExtraFields.active_ctx.value]:
                return key
        return None

    async def _read_pac_ctx(self, storage_key: str) -> Tuple[Dict, Optional[str]]:
        primary_id = await self._get_last_ctx(storage_key)
        if primary_id is not None:
            return self.context_dict[primary_id][self._PACKED_COLUMN], primary_id
        else:
            return dict(), None

    async def _read_log_ctx(self, keys_limit: Optional[int], field_name: str, primary_id: str) -> Dict:
        key_set = [k for k in sorted(self.log_dict[primary_id][field_name].keys(), reverse=True)]
        keys = key_set if keys_limit is None else key_set[:keys_limit]
        return {k: self.log_dict[primary_id][field_name][k][self._VALUE_COLUMN] for k in keys}

    async def _write_pac_ctx(self, data: Dict, created: datetime, updated: datetime, storage_key: str, primary_id: str):
        self.context_dict[primary_id] = {
            ExtraFields.storage_key.value: storage_key,
            ExtraFields.active_ctx.value: True,
            self._PACKED_COLUMN: data,
            ExtraFields.created_at.value: created,
            ExtraFields.updated_at.value: updated,
        }

    async def _write_log_ctx(self, data: List[Tuple[str, int, Dict]], updated: datetime, primary_id: str):
        for field, key, value in data:
            self.log_dict.setdefault(primary_id, dict()).setdefault(field, dict()).setdefault(key, {
                self._VALUE_COLUMN: value,
                ExtraFields.updated_at.value: updated,
            })


# %%
pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=MemoryContextStorage())

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    # This is a function for automatic tutorial running (testing) with HAPPY_PATH

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
