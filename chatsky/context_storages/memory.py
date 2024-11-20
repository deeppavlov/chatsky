from typing import List, Optional, Set, Tuple

from .database import DBContextStorage, _SUBSCRIPT_DICT


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
        }

    async def load_main_info(self, ctx_id: str) -> Optional[Tuple[int, int, int, bytes, bytes]]:
        return self._main_storage.get(ctx_id, None)

    async def update_main_info(
        self, ctx_id: str, turn_id: int, crt_at: int, upd_at: int, misc: bytes, fw_data: bytes
    ) -> None:
        self._main_storage[ctx_id] = (turn_id, crt_at, upd_at, misc, fw_data)

    async def delete_context(self, ctx_id: str) -> None:
        self._main_storage.pop(ctx_id, None)
        for storage in self._aux_storage.values():
            storage.pop(ctx_id, None)

    @DBContextStorage._verify_field_name
    async def load_field_latest(self, ctx_id: str, field_name: str) -> List[Tuple[int, bytes]]:
        select = sorted(
            [k for k, v in self._aux_storage[field_name].get(ctx_id, dict()).items() if v is not None], reverse=True
        )
        if isinstance(self._subscripts[field_name], int):
            select = select[: self._subscripts[field_name]]
        elif isinstance(self._subscripts[field_name], Set):
            select = [k for k in select if k in self._subscripts[field_name]]
        return [(k, self._aux_storage[field_name][ctx_id][k]) for k in select]

    @DBContextStorage._verify_field_name
    async def load_field_keys(self, ctx_id: str, field_name: str) -> List[int]:
        return [k for k, v in self._aux_storage[field_name].get(ctx_id, dict()).items() if v is not None]

    @DBContextStorage._verify_field_name
    async def load_field_items(self, ctx_id: str, field_name: str, keys: List[int]) -> List[Tuple[int, bytes]]:
        return [
            (k, v) for k, v in self._aux_storage[field_name].get(ctx_id, dict()).items() if k in keys and v is not None
        ]

    @DBContextStorage._verify_field_name
    async def update_field_items(self, ctx_id: str, field_name: str, items: List[Tuple[int, Optional[bytes]]]) -> None:
        self._aux_storage[field_name].setdefault(ctx_id, dict()).update(items)

    async def clear_all(self) -> None:
        self._main_storage = dict()
        for key in self._aux_storage.keys():
            self._aux_storage[key] = dict()
