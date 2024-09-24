import asyncio
from typing import Dict, List, Optional, Set, Tuple

from .database import DBContextStorage, FieldConfig


class MemoryContextStorage(DBContextStorage):
    """
    Implements :py:class:`.DBContextStorage` storing contexts in memory, wthout file backend.
    Uses :py:class:`.JsonSerializer` as the default serializer.
    By default it sets path to an empty string.

    Keeps data in a dictionary and two lists:
    
    - `main`: {context_id: [created_at, turn_id, updated_at, framework_data]}
    - `turns`: [context_id, turn_number, label, request, response]
    - `misc`: [context_id, turn_number, misc]
    """

    is_asynchronous = True

    def __init__(
        self, 
        path: str = "",
        rewrite_existing: bool = False,
        configuration: Optional[Dict[str, FieldConfig]] = None,
    ):
        DBContextStorage.__init__(self, path, rewrite_existing, configuration)
        asyncio.run(self.clear_all())

    def _get_table_field_and_config(self, field_name: str) -> Tuple[List, int, FieldConfig]:
        if field_name == self.labels_config.name:
            return self._storage[self._turns_table_name], 2, self.labels_config
        elif field_name == self.requests_config.name:
            return self._storage[self._turns_table_name], 3, self.requests_config
        elif field_name == self.responses_config.name:
            return self._storage[self._turns_table_name], 4, self.responses_config
        elif field_name == self.misc_config.name:
            return self._storage[self.misc_config.name], 2, self.misc_config
        else:
            raise ValueError(f"Unknown field name: {field_name}!")

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes]]:
        return self._storage[self._main_table_name].get(ctx_id, None)

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, fw_data: bytes) -> None:
        self._storage[self._main_table_name][ctx_id] = (turn_id, crt_at, upd_at, fw_data)

    async def delete_main_info(self, ctx_id: str) -> None:
        self._storage[self._main_table_name].pop(ctx_id)
        self._storage[self._turns_table_name] = [e for e in self._storage[self._turns_table_name] if e[0] != ctx_id]
        self._storage[self.misc_config.name] = [e for e in self._storage[self.misc_config.name] if e[0] != ctx_id]

    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[str, bytes]]:
        field_table, field_idx, field_config = self._get_table_field_and_config(field_name)
        select = [e for e in field_table if e[0] == ctx_id]
        if field_name != self.misc_config.name:
            select = sorted(select, key=lambda x: int(x[1]), reverse=True)
        if isinstance(field_config.subscript, int):
            select = select[:field_config.subscript]
        elif isinstance(field_config.subscript, Set):
            select = [e for e in select if e[1] in field_config.subscript]
        return [(e[1], e[field_idx]) for e in select]

    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[str]:
        field_table, _, _ = self._get_table_field_and_config(field_name)
        return [e[1] for e in field_table if e[0] == ctx_id]

    async def load_field_items(self, ctx_id: str, field_name: str, keys: List[str]) -> List[bytes]:
        field_table, field_idx, _ = self._get_table_field_and_config(field_name)
        return [e[field_idx] for e in field_table if e[0] == ctx_id and e[1] in keys]

    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[str, bytes]]) -> None:
        field_table, field_idx, _ = self._get_table_field_and_config(field_name)
        while len(items) > 0:
            nx = items.pop(0)
            for i in range(len(field_table)):
                if field_table[i][0] == ctx_id and field_table[i][1] == nx[0]:
                    field_table[i][field_idx] = nx[1]
                    break
            else:
                if field_name == self.misc_config.name:
                    field_table.append([ctx_id, nx[0], None])
                else:
                    field_table.append([ctx_id, nx[0], None, None, None])
                field_table[-1][field_idx] = nx[1]

    async def clear_all(self) -> None:
        self._storage = {
            self._main_table_name: dict(),
            self._turns_table_name: list(),
            self.misc_config.name: list(),
        }
