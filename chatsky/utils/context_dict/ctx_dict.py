from hashlib import sha256
from typing import Any, Callable, Dict, Generic, Hashable, List, Mapping, Optional, Sequence, Set, Tuple, Type, TypeVar, Union

from pydantic import BaseModel, PrivateAttr, model_serializer, model_validator

from chatsky.context_storages.database import DBContextStorage
from .asyncronous import launch_coroutines

K, V = TypeVar("K", bound=Hashable), TypeVar("V", bound=BaseModel)


def get_hash(string: str) -> bytes:
    return sha256(string.encode()).digest()


class ContextDict(BaseModel, Generic[K, V]):
    _items: Dict[K, V] = PrivateAttr(default_factory=dict)
    _hashes: Dict[K, int] = PrivateAttr(default_factory=dict)
    _keys: Set[K] = PrivateAttr(default_factory=set)
    _added: Set[K] = PrivateAttr(default_factory=set)
    _removed: Set[K] = PrivateAttr(default_factory=set)

    _storage: Optional[DBContextStorage] = PrivateAttr(None)
    _ctx_id: str = PrivateAttr(default_factory=str)
    _field_name: str = PrivateAttr(default_factory=str)
    _field_constructor: Callable[[Dict[str, Any]], V] = PrivateAttr(default_factory=dict)

    _marker: object = PrivateAttr(object())

    @property
    def _key_list(self) -> List[K]:
        return sorted(list(self._keys))

    @classmethod
    async def new(cls, storage: DBContextStorage, id: str, field: str) -> "ContextDict":
        instance = cls()
        instance._storage = storage
        instance._ctx_id = id
        instance._field_name = field
        return instance

    @classmethod
    async def connected(cls, storage: DBContextStorage, id: str, field: str, constructor: Type[V]) -> "ContextDict":
        keys, items = await launch_coroutines([storage.load_field_keys(id, field), storage.load_field_latest(id, field)], storage.is_asynchronous)
        hashes = {k: get_hash(v) for k, v in items}
        objected = {k: constructor.model_validate_json(v) for k, v in items}
        instance = cls.model_validate(objected)
        instance._storage = storage
        instance._ctx_id = id
        instance._field_name = field
        instance._field_constructor = constructor
        instance._keys = set(keys)
        instance._hashes = hashes
        return instance

    async def _load_items(self, keys: List[K]) -> Dict[K, V]:
        items = await self._storage.load_field_items(self._ctx_id, self._field_name, set(keys))
        for key, item in zip(keys, items):
            self._items[key] = self._field_constructor.model_validate_json(item)
            if self._storage.rewrite_existing:
                self._hashes[key] = get_hash(item)

    async def __getitem__(self, key: Union[K, slice]) -> Union[V, List[V]]:
        if self._storage is not None:
            if isinstance(key, slice):
                await self._load_items([self._key_list[k] for k in range(len(self._keys))[key] if k not in self._items.keys()])
            elif key not in self._items.keys():
                await self._load_items([key])
        if isinstance(key, slice):
            return [self._items[self._key_list[k]] for k in range(len(self._items.keys()))[key]]
        else:
            return self._items[key]

    def __setitem__(self, key: Union[K, slice], value: Union[V, Sequence[V]]) -> None:
        if isinstance(key, slice) and isinstance(value, Sequence):
            key_slice = list(range(len(self._keys))[key])
            if len(key_slice) != len(value):
                raise ValueError("Slices must have the same length!")
            for k, v in zip([self._key_list[k] for k in key_slice], value):
                self[k] = v
        elif not isinstance(key, slice) and not isinstance(value, Sequence):
            self._keys.add(key)
            self._added.add(key)
            self._removed.discard(key)
            self._items[key] = value
        else:
            raise ValueError("Slice key must have sequence value!")

    def __delitem__(self, key: Union[K, slice]) -> None:
        if isinstance(key, slice):
            for i in [self._key_list[k] for k in range(len(self._keys))[key]]:
                del self[i]
        else:
            self._removed.add(key)
            self._added.discard(key)
            self._keys.discard(key)
            del self._items[key]

    def __iter__(self) -> Sequence[K]:
        return iter(self._keys if self._storage is not None else self._items.keys())
    
    def __len__(self) -> int:
        return len(self._keys if self._storage is not None else self._items.keys())

    async def get(self, key: K, default: V = _marker) -> V:
        try:
            return await self[key]
        except KeyError:
            if default is self._marker:
                raise
            return default

    def __contains__(self, key: K) -> bool:
        return key in self.keys()

    def keys(self) -> Set[K]:
        return set(iter(self))

    async def values(self) -> List[V]:
        return await self[:]

    async def items(self) -> List[Tuple[K, V]]:
        return [(k, v) for k, v in zip(self.keys(), await self.values())]

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

    def clear(self) -> None:
        del self[:]

    async def update(self, other: Any = (), /, **kwds) -> None:
        if isinstance(other, ContextDict):
            self.update(zip(other.keys(), await other.values()))
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

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ContextDict):
            return False
        return (
            self._items == value._items
            and self._hashes == value._hashes
            and self._added == value._added
            and self._removed == value._removed
            and self._storage == value._storage
            and self._ctx_id == value._ctx_id
            and self._field_name == value._field_name
        )

    def __repr__(self) -> str:
        return f"ContextStorage(items={self._items}, hashes={self._hashes}, added={self._added}, removed={self._removed}, storage={self._storage}, ctx_id={self._ctx_id}, field_name={self._field_name})"

    @model_validator(mode="wrap")
    def _validate_model(value: Dict[K, V], handler: Callable[[Dict], "ContextDict"]) -> "ContextDict":
        instance = handler(dict())
        instance._items = {k: v for k, v in value.items()}
        instance._keys = set(value.keys())
        return instance

    @model_serializer(when_used="json")
    def _serialize_model(self) -> Dict[K, V]:
        if self._storage is None:
            return self._items
        elif self._storage.rewrite_existing:
            result = dict()
            for k, v in self._items.items():
                byted = v.model_dump_json()
                if get_hash(byted) != self._hashes.get(k, None):
                    result.update({k: byted})
            return result
        else:
            return {k: self._items[k] for k in self._added}

    async def store(self) -> None:
        if self._storage is not None:
            byted = [(k, v) for k, v in self.model_dump(mode="json").items()]
            await launch_coroutines(
                [
                    self._storage.update_field_items(self._ctx_id, self._field_name, byted),
                    self._storage.delete_field_keys(self._ctx_id, self._field_name, list(self._removed - self._added)),
                ],
                self._storage.is_asynchronous,
            )
        else:
            raise RuntimeError(f"{type(self).__name__} is not attached to any context storage!")
