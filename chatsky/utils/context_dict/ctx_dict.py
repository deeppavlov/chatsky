from typing import Any, Callable, Dict, Generic, List, Mapping, Optional, Sequence, Set, Tuple, TypeVar

from pydantic import BaseModel, Field, PrivateAttr, model_serializer, model_validator

from chatsky.context_storages.database import DBContextStorage

K, V = TypeVar("K"), TypeVar("V")


class ContextDict(BaseModel, Generic[K, V]):
    write_full_diff: bool = Field(False)
    _attached: bool = PrivateAttr(False)
    _items: Dict[K, V] = PrivateAttr(default_factory=dict)
    _keys: List[K] = PrivateAttr(default_factory=list)

    _storage: Optional[DBContextStorage] = PrivateAttr(None)
    _ctx_id: str = PrivateAttr(default_factory=str)
    _field_name: str = PrivateAttr(default_factory=str)
    _hashes: Dict[K, int] = PrivateAttr(default_factory=dict)
    _added: List[K] = PrivateAttr(default_factory=list)

    _marker: object = PrivateAttr(object())

    @classmethod
    async def connect(cls, storage: DBContextStorage, id: str, field: str) -> "ContextDict":
        instance = cls()
        instance._attached = True
        instance._storage = storage
        instance._ctx_id = id
        instance._field_name = field
        instance._items = await storage.load_field_latest(id, field)
        instance._keys = await storage.load_field_keys(id, field)
        instance._hashes = {k: hash(v) for k, v in instance._items.items()}
        return instance

    async def __getitem__(self, key: K) -> V:
        if key not in self._items.keys() and self._attached:
            self._items[key] = await self._storage.load_field_item(self._ctx_id, self._field_name, key)
            self._hashes[key] = hash(self._items[key])
        return self._items[key]

    def __setitem__(self, key: K, value: V) -> None:
        if self._attached:
            self._added += [key]
            self._hashes[key] = None
        self._items[key] = value

    def __delitem__(self, key: K) -> None:
        if self._attached:
            self._added = [v for v in self._added if v is not key]
            self._items[key] = None
        else:
            del self._items[key]

    def __iter__(self) -> Sequence[K]:
        return iter(self._keys if self._attached else self._items.keys())
    
    def __len__(self) -> int:
        return len(self._keys if self._attached else self._items.keys())

    async def get(self, key: K, default: V = _marker) -> V:
        try:
            return await self[key]
        except KeyError:
            if default is self._marker:
                raise
            return default

    def keys(self) -> Set[K]:
        return set(iter(self))

    def __contains__(self, key: K) -> bool:
        return key in self.keys()

    async def items(self) -> Set[Tuple[K, V]]:
        return {(k, await self[k]) for k in self.keys()}

    async def values(self) -> Set[V]:
        return {await self[k] for k in self.keys()}

    async def pop(self, key: K, default: V = _marker) -> V:
        try:
            value = await self[key]
        except KeyError:
            if default is self._marker:
                raise
            return default
        else:
            del self[key]
            return value

    async def popitem(self) -> Tuple[K, V]:
        try:
            key = next(iter(self))
        except StopIteration:
            raise KeyError from None
        value = await self[key]
        del self[key]
        return key, value

    async def clear(self) -> None:
        try:
            while True:
                await self.popitem()
        except KeyError:
            pass

    async def update(self, other: Any = (), /, **kwds) -> None:
        if isinstance(other, ContextDict):
            for key in other:
                self[key] = await other[key]
        elif isinstance(other, Mapping):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, "keys"):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    async def setdefault(self, key: K, default: V = _marker) -> V:
        try:
            return await self[key]
        except KeyError:
            if default is self._marker:
                raise
            self[key] = default
        return default

    @model_validator(mode="wrap")
    def _validate_model(value: Dict[K, V], handler: Callable[[Dict], "ContextDict"]) -> "ContextDict":
        instance = handler(dict())
        instance._items = value
        return instance

    @model_serializer()
    def _serialize_model(self) -> Dict[K, V]:
        if not self._attached:
            return self._items
        elif self.write_full_diff:
            return {k: v for k, v in self._items.items() if hash(v) != self._hashes[k]}
        else:
            return {k: self._items[k] for k in self._added}
