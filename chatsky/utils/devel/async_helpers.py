"""
Async Helpers
-------------
Tools to help with async.
"""

import asyncio
from typing import Callable, Any


async def wrap_sync_function_in_async(func: Callable, *args, **kwargs) -> Any:
    """
    Utility function, that wraps both functions and coroutines in coroutines.
    Invokes `func` if it is just a callable and awaits, if this is a coroutine.

    :param func: Callable to wrap.
    :param \\*args: Function args.
    :param \\**kwargs: Function kwargs.
    :return: What function returns.
    """
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


async def async_infinite_sleep() -> None:
    """Utility function that awaits for infinity"""
    while True:
        await asyncio.sleep(3600)


async def async_do_nothing() -> None:
    """An async utility function that does nothing"""
    pass
