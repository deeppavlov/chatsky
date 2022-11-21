import functools
from typing import Callable, Optional


USED_CACHES = list()


def cache_clear():
    for used_cache in USED_CACHES:
        used_cache.cache_clear()


def lru_cache(maxsize: Optional[int] = None, typed: bool = False) -> Callable:
    global USED_CACHES

    def decorator(func):
        global USED_CACHES

        @functools.lru_cache(maxsize=maxsize, typed=typed)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        USED_CACHES += [wrapper]
        return wrapper

    return decorator


def cache(func, /):
    return lru_cache(maxsize=None)(func)
