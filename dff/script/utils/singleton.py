import functools
from typing import Callable, Optional


USED_CACHES = list()


def clean_cache_singleton():
    for cache in USED_CACHES:
        cache.cache_clear()


def singleton_cache(maxsize: Optional[int] = None, typed: bool = False) -> Callable:
    global USED_CACHES

    def decorator(func):
        global USED_CACHES

        @functools.lru_cache(maxsize=maxsize, typed=typed)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        USED_CACHES += [wrapper]
        return wrapper

    return decorator
