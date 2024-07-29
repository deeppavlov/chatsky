from typing import Dict, MutableMapping, Sequence, TypeVar

from chatsky.context_storages.database import DBContextStorage

K, V = TypeVar("K"), TypeVar("V")


class ContextDict(MutableMapping[K, V]):
    async def __new__(cls, *args, **kwargs) -> "ContextDict":
        instance = super().__new__(cls)
        await instance.__init__(*args, **kwargs)
        return instance

    async def __init__(self, storage: DBContextStorage, id: str, field: str) -> None:
        self._ctx_id = id
        self._field_name = field
        self._storage = storage
        self._items = storage.load_field_latest(id, field)
        self._hashes = {k: hash(v) for k, v in self._items.items()}
        self._added = list()
        self.write_full_diff = False

    def __getitem__(self, key: K) -> V:
        if key not in self._items.keys():
            self._items[key] = self._storage.load_field_item(self._ctx_id, self._field_name, key)
            self._hashes[key] = hash(self._items[key])
        return self._items[key]

    def __setitem__(self, key: K, value: V) -> None:
        self._added += [key]
        self._hashes[key] = None
        self._items[key] = value

    def __delitem__(self, key: K) -> None:
        self._added = [v for v in self._added if v is not key]
        self._items[key] = None

    def __iter__(self) -> Sequence[K]:
        return iter(self._storage.load_field_keys(self._ctx_id, self._field_name))
    
    def __len__(self) -> int:
        return len(self._storage.load_field_keys(self._ctx_id, self._field_name))

    def diff(self) -> Dict[K, V]:
        if self.write_full_diff:
            return {k: v for k, v in self._items.items() if hash(v) != self._hashes[k]}
        else:
            return {k: self._items[k] for k in self._added}
