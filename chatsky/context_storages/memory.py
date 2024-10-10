from typing import Dict, List, Optional, Set, Tuple, Hashable

from .database import DBContextStorage, _SUBSCRIPT_DICT, _SUBSCRIPT_TYPE


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
        configuration: Optional[_SUBSCRIPT_DICT] = None,
    ):
        DBContextStorage.__init__(self, path, rewrite_existing, configuration)
        self._main_storage = dict()
        self._aux_storage = {
            self._labels_field_name: dict(),
            self._requests_field_name: dict(),
            self._responses_field_name: dict(),
            self._misc_field_name: dict(),
        }

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes]]:
        return self._main_storage.get(ctx_id, None)

    async def update_main_info(self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, fw_data: bytes) -> None:
        self._main_storage[ctx_id] = (turn_id, crt_at, upd_at, fw_data)

    async def delete_context(self, ctx_id: str) -> None:
        self._main_storage.pop(ctx_id, None)
        for storage in self._aux_storage.values():
            storage.pop(ctx_id, None)

    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[Hashable, bytes]]:
        subscript = self._get_subscript_for_field(field_name)
        select = [k for k, v in self._aux_storage[field_name].get(ctx_id, dict()).items() if v is not None]
        if field_name != self._misc_field_name:
            select = sorted(select, key=lambda x: x, reverse=True)
        if isinstance(subscript, int):
            select = select[:subscript]
        elif isinstance(subscript, Set):
            select = [k for k in select if k in subscript]
        return [(k, self._aux_storage[field_name][ctx_id][k]) for k in select]

    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[Hashable]:
        return [k for k, v in self._aux_storage[field_name].get(ctx_id, dict()).items() if v is not None]

    async def load_field_items(self, ctx_id: str, field_name: str, keys: List[Hashable]) -> List[bytes]:
        return [(k, v) for k, v in self._aux_storage[field_name].get(ctx_id, dict()).items() if k in keys and v is not None]

    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[Hashable, bytes]]) -> None:
        self._aux_storage[field_name].setdefault(ctx_id, dict()).update(items)

    async def clear_all(self) -> None:
        self._main_storage = dict()
        for key in self._aux_storage.keys():
            self._aux_storage[key] = dict()
