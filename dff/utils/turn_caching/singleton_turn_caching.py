"""
Singleton Turn Caching
----------------------
This module contains functions for caching function results on each dialog turn.
"""
import functools
from typing import Callable, List, Optional


USED_CACHES: List[Callable] = list()
"""Cache singleton, it is common for all actors and pipelines in current environment."""


def cache_clear():
    """
    Function for cache singleton clearing, it is called in the end of pipeline execution turn.
    """
    for used_cache in USED_CACHES:
        used_cache.cache_clear()


def lru_cache(maxsize: Optional[int] = None, typed: bool = False) -> Callable:
    """
    Decorator function for caching function results in scripts.
    Works like the standard :py:func:`~functools.lru_cache` function.
    Caches are kept in a library-wide singleton and cleared in the end of each turn.
    """

    def decorator(func):
        global USED_CACHES

        @functools.wraps(func)
        @functools.lru_cache(maxsize=maxsize, typed=typed)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        USED_CACHES += [wrapper]
        return wrapper

    return decorator


def cache(func):
    """
    Decorator function for caching function results in scripts.
    Works like the standard :py:func:`~functools.cache` function.
    Caches are kept in a library-wide singleton and cleared in the end of each turn.
    """
    return lru_cache(maxsize=None)(func)
