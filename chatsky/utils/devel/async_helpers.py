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
    Invokes `func` if it is just a callable and awaits, if it is a coroutine.

    :param func: Callable to wrap.
    :param \\*args: Function args.
    :param \\**kwargs: Function kwargs.
    :return: What function returns.
    """
    result = func(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    else:
        return result
