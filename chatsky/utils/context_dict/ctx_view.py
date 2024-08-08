from typing import Any, Callable, Mapping, Sequence, Set, Tuple, TypeVar

from .ctx_dict import ContextDict


K, V, N = TypeVar("K"), TypeVar("V"), TypeVar("N")


class ContextDictView(Mapping[K, N]):
    _marker = object()

    def __init__(self, context_dict: ContextDict[K, V], get_mapping: Callable[[V], N], set_mapping: Callable[[V, N], V]) -> None:
        super().__init__()
        self._context_dict = context_dict
        self._get_mapping_lambda = get_mapping
        self._set_mapping_lambda = set_mapping
    
    async def __getitem__(self, key: K) -> N:
        return self._get_mapping_lambda(await self._context_dict[key])

    def __setitem__(self, key: K, value: N) -> None:
        self._context_dict[key] = self._set_mapping_lambda(key, value)

    def __iter__(self) -> Sequence[K]:
        return iter(self._context_dict)

    def __len__(self) -> int:
        return len(self._context_dict)

    async def get(self, key: K, default: N = _marker) -> N:
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

    async def values(self) -> Set[N]:
        return set(await self[:])

    async def items(self) -> Set[Tuple[K, N]]:
        return tuple(zip(self.keys(), await self.values()))

    def update(self, other: Any = (), /, **kwds) -> None:
        if isinstance(other, Mapping):
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
