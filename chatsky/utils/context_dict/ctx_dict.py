from asyncio import gather
from typing import Any, Awaitable, Callable, Dict, Generic, List, Mapping, Optional, Sequence, Set, Tuple, TypeVar, Union, Literal

from pydantic import BaseModel, PrivateAttr, model_serializer, model_validator

from chatsky.context_storages.database import DBContextStorage

K, V = TypeVar("K"), TypeVar("V")


async def launch_coroutines(coroutines: List[Awaitable], is_async: bool) -> List[Any]:
    if is_async:
        return await gather(*coroutines)
    else:
        return [await coroutine for coroutine in coroutines]


class ContextDict(BaseModel, Generic[K, V]):
    WRITE_KEY: Literal["WRITE"] = "WRITE"
    DELETE_KEY: Literal["DELETE"] = "DELETE"

    _items: Dict[K, V] = PrivateAttr(default_factory=dict)
    _keys: List[K] = PrivateAttr(default_factory=list)
    _hashes: Dict[K, int] = PrivateAttr(default_factory=dict)
    _added: List[K] = PrivateAttr(default_factory=list)
    _removed: List[K] = PrivateAttr(default_factory=list)

    _storage: Optional[DBContextStorage] = PrivateAttr(None)
    _ctx_id: str = PrivateAttr(default_factory=str)
    _field_name: str = PrivateAttr(default_factory=str)
    _field_constructor: Callable[[Dict[str, Any]], V] = PrivateAttr(default_factory=dict)

    _marker: object = PrivateAttr(object())

    @classmethod
    async def new(cls, storage: DBContextStorage, id: str) -> "ContextDict":
        instance = cls()
        instance._storage = storage
        instance._ctx_id = id
        return instance

    @classmethod
    async def connected(cls, storage: DBContextStorage, id: str, field: str, constructor: Callable[[Dict[str, Any]], V] = dict) -> "ContextDict":
        keys, items = await launch_coroutines([storage.load_field_keys(id, field), storage.load_field_latest(id, field)], storage.is_asynchronous)
        hashes = {k: hash(v) for k, v in items.items()}
        instance = cls.model_validate(items)
        instance._storage = storage
        instance._ctx_id = id
        instance._field_name = field
        instance._field_constructor = constructor
        instance._keys = keys
        instance._hashes = hashes
        return instance

    async def _load_items(self, keys: List[K]) -> Dict[K, V]:
        items = await self._storage.load_field_items(self._ctx_id, self._field_name, keys)
        for key, item in zip(keys, items):
            self._items[key] = self._field_constructor(item)
            self._hashes[key] = hash(item)

    async def __getitem__(self, key: Union[K, slice]) -> V:
        if self._storage is not None and self._storage.rewrite_existing:
            if isinstance(key, slice):
                await self._load_items([k for k in range(len(self._keys))[key] if k not in self._items.keys()])
            elif key not in self._items.keys():
                await self._load_items([key])
        if isinstance(key, slice):
            return {k: await self._items[k] for k in range(len(self._items.keys()))[key]}
        else:
            return self._items[key]

    def __setitem__(self, key: Union[K, slice], value: Union[V, Sequence[V]]) -> None:
        if isinstance(key, slice) and isinstance(value, Sequence):
            if len(key) != len(value):
                raise ValueError("Slices must have the same length!")
            for k, v in zip(range(len(self._keys))[key], value):
                self[k] = v
        elif not isinstance(key, slice) and not isinstance(value, Sequence):
            self._keys += [key]
            if key not in self._items.keys():
                self._added += [key]
            if key in self._removed:
                self._removed.remove(key)
            self._items[key] = value
        else:
            raise ValueError("Slice key must have sequence value!")

    def __delitem__(self, key: Union[K, slice]) -> None:
        if isinstance(key, slice):
            for k in range(len(self._keys))[key]:
                del self[k]
        else:
            self._removed += [key]
            if key in self._items.keys():
                self._keys.remove(key)
            if key in self._added:
                self._added.remove(key)
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
        instance._items = {key: value[key] for key in sorted(value)}
        return instance

    @model_serializer()
    def _serialize_model(self) -> Dict[K, V]:
        if self._storage is None:
            return self._items
        elif self._storage.rewrite_existing:
            return {k: v for k, v in self._items.items() if hash(v) != self._hashes[k]}
        else:
            return {k: self._items[k] for k in self._added}

    async def store(self) -> None:
        if self._storage is not None:
            await launch_coroutines(
                [
                    self._storage.update_field_items(self._ctx_id, self._field_name, self.model_dump()),
                    self._storage.delete_field_keys(self._ctx_id, self._field_name, self._removed),
                ],
                self._storage.is_asynchronous,
            )
        else:
            raise RuntimeError("ContextDict is not attached to any context storage!")
