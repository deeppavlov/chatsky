from __future__ import annotations
from hashlib import sha256
from typing import Any, Callable, Dict, Generic, List, Mapping, Optional, Sequence, Set, Tuple, Type, TypeVar, Union, overload, TYPE_CHECKING

from pydantic import BaseModel, PrivateAttr, TypeAdapter, model_serializer, model_validator

from .asyncronous import launch_coroutines

if TYPE_CHECKING:
    from chatsky.context_storages.database import DBContextStorage

K = TypeVar("K", bound=int)
V = TypeVar("V")


def get_hash(string: bytes) -> bytes:
    return sha256(string).digest()


class ContextDict(BaseModel, Generic[K, V]):
    _items: Dict[K, V] = PrivateAttr(default_factory=dict)
    _hashes: Dict[K, int] = PrivateAttr(default_factory=dict)
    _keys: Set[K] = PrivateAttr(default_factory=set)
    _added: Set[K] = PrivateAttr(default_factory=set)
    _removed: Set[K] = PrivateAttr(default_factory=set)

    _storage: Optional[DBContextStorage] = PrivateAttr(None)
    _ctx_id: str = PrivateAttr(default_factory=str)
    _field_name: str = PrivateAttr(default_factory=str)
    _value_type: Optional[TypeAdapter[Type[V]]] = PrivateAttr(None)

    @classmethod
    async def new(cls, storage: DBContextStorage, id: str, field: str, value_type: Type[V]) -> "ContextDict":
        instance = cls()
        instance._storage = storage
        instance._ctx_id = id
        instance._field_name = field
        instance._value_type = TypeAdapter(value_type)
        return instance

    @classmethod
    async def connected(cls, storage: DBContextStorage, id: str, field: str, value_type: Type[V]) -> "ContextDict":
        val_adapter = TypeAdapter(value_type)
        keys, items = await launch_coroutines([storage.load_field_keys(id, field), storage.load_field_latest(id, field)], storage.is_asynchronous)
        val_key_items = [(k, v) for k, v in items if v is not None]
        hashes = {k: get_hash(v) for k, v in val_key_items}
        objected = {k: val_adapter.validate_json(v) for k, v in val_key_items}
        instance = cls.model_validate(objected)
        instance._storage = storage
        instance._ctx_id = id
        instance._field_name = field
        instance._value_type = val_adapter
        instance._keys = set(keys)
        instance._hashes = hashes
        return instance

    async def _load_items(self, keys: List[K]) -> Dict[K, V]:
        items = await self._storage.load_field_items(self._ctx_id, self._field_name, keys)
        for key, value in items.items():
            self._items[key] = self._value_type.validate_json(value)
            if not self._storage.rewrite_existing:
                self._hashes[key] = get_hash(value)

    @overload
    async def __getitem__(self, key: K) -> V: ...

    @overload
    async def __getitem__(self, key: slice) -> List[V]: ...

    async def __getitem__(self, key):
        if isinstance(key, int) and key < 0:
            key = self.keys()[key]
        if self._storage is not None:
            if isinstance(key, slice):
                await self._load_items([self.keys()[k] for k in range(len(self.keys()))[key] if k not in self._items.keys()])
            elif key not in self._items.keys():
                await self._load_items([key])
        if isinstance(key, slice):
            return [self._items[k] for k in self.keys()[key]]
        else:
            return self._items[key]

    def __setitem__(self, key: Union[K, slice], value: Union[V, Sequence[V]]) -> None:
        if isinstance(key, int) and key < 0:
            key = self.keys()[key]
        if isinstance(key, slice):
            if isinstance(value, Sequence):
                key_slice = self.keys()[key]
                if len(key_slice) != len(value):
                    raise ValueError("Slices must have the same length!")
                for k, v in zip(key_slice, value):
                    self[k] = v
            else:
                raise ValueError("Slice key must have sequence value!")
        else:
            self._keys.add(key)
            self._added.add(key)
            self._removed.discard(key)
            self._items[key] = self._value_type.validate_python(value)

    def __delitem__(self, key: Union[K, slice]) -> None:
        if isinstance(key, int) and key < 0:
            key = self.keys()[key]
        if isinstance(key, slice):
            for k in self.keys()[key]:
                del self[k]
        else:
            self._removed.add(key)
            self._added.discard(key)
            self._keys.discard(key)
            del self._items[key]

    def __iter__(self) -> Sequence[K]:
        return iter(self.keys() if self._storage is not None else self._items.keys())
    
    def __len__(self) -> int:
        return len(self.keys() if self._storage is not None else self._items.keys())

    async def get(self, key: K, default = None) -> V:
        try:
            return await self[key]
        except KeyError:
            return default

    def __contains__(self, key: K) -> bool:
        return key in self.keys()

    def keys(self) -> List[K]:
        return sorted(self._keys)

    async def values(self) -> List[V]:
        return await self[:]

    async def items(self) -> List[Tuple[K, V]]:
        return [(k, v) for k, v in zip(self.keys(), await self.values())]

    async def pop(self, key: K, default = None) -> V:
        try:
            value = await self[key]
        except KeyError:
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

    def clear(self) -> None:
        del self[:]

    async def update(self, other: Any = (), /, **kwds) -> None:
        if isinstance(other, ContextDict):
            await self.update(zip(other.keys(), await other.values()))
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

    async def setdefault(self, key: K, default = None) -> V:
        try:
            return await self[key]
        except KeyError:
            self[key] = default
        return default

    def __eq__(self, value: object) -> bool:
        if isinstance(value, ContextDict):
            return self._items == value._items
        elif isinstance(value, Dict):
            return self._items == value
        else:
            return False

    def __repr__(self) -> str:
        return f"ContextDict(items={self._items}, keys={list(self.keys())}, hashes={self._hashes}, added={self._added}, removed={self._removed}, storage={self._storage}, ctx_id={self._ctx_id}, field_name={self._field_name})"

    @model_validator(mode="wrap")
    def _validate_model(value: Any, handler: Callable[[Any], "ContextDict"], _) -> "ContextDict":
        if isinstance(value, ContextDict):
            return value
        elif isinstance(value, Dict):
            instance = handler(dict())
            instance._items = value.copy()
            instance._keys = set(value.keys())
            return instance
        else:
            raise ValueError(f"Unknown type of ContextDict value: {type(value).__name__}!")

    @model_serializer()
    def _serialize_model(self) -> Dict[K, V]:
        if self._storage is None:
            return self._items
        elif not self._storage.rewrite_existing:
            result = dict()
            for k, v in self._items.items():
                value = self._value_type.dump_json(v)
                if get_hash(value) != self._hashes.get(k, None):
                    result[k] = value.decode()
            return result
        else:
            return {k: self._value_type.dump_json(self._items[k]).decode() for k in self._added}

    async def store(self) -> None:
        if self._storage is not None:
            await launch_coroutines(
                [
                    self._storage.update_field_items(self._ctx_id, self._field_name, [(k, e.encode()) for k, e in self.model_dump().items()]),
                    self._storage.delete_field_keys(self._ctx_id, self._field_name, list(self._removed - self._added)),
                ],
                self._storage.is_asynchronous,
            )
            if not self._storage.rewrite_existing:
                for k, v in self._items.items():
                    value_hash = get_hash(self._value_type.dump_json(v))
                    if value_hash != self._hashes.get(k, None):
                        self._hashes[k] = value_hash
        else:
            raise RuntimeError(f"{type(self).__name__} is not attached to any context storage!")
