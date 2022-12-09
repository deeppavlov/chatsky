"""
Utils
------
This module contains utilities for the telegram connector.
"""
from functools import wraps
from typing import Callable
from typing_extensions import ParamSpec, TypeVar
from pathlib import Path
from io import IOBase
from copy import copy

from telebot import types

TELEGRAM_STATE_KEY = "TELEGRAM_MESSENGER"
_P = ParamSpec("_P")
_R = TypeVar("_R")


def partialmethod(func: Callable[_P, _R], **part_kwargs) -> Callable[_P, _R]:
    """
    This function replaces the `partialmethod` implementation from functools.
    In contrast with the original class-based approach, it decorates the function, so we can use docstrings.
    """
    newfunc = copy(func)
    newfunc.__doc__ = func.__doc__.format(**part_kwargs)

    @wraps(newfunc)
    def wrapper(self, *args: _P.args, **kwargs: _P.kwargs):
        kwargs = {**kwargs, **part_kwargs}
        return newfunc(self, *args, **kwargs)

    doc: str = newfunc.__doc__
    wrapper.__doc__ = doc.format(**part_kwargs)

    return wrapper


def open_io(item: types.InputMedia):
    """Returns a copy of `InputMedia` with an opened file descriptor instead of path."""
    copied_item = copy(item)
    if isinstance(copied_item.media, Path):
        copied_item.media = copied_item.media.open(mode="rb")
    return copied_item


def close_io(item: types.InputMedia):
    """Closes an IO in an `InputMedia` object to perform the cleanup."""
    if isinstance(item.media, IOBase):
        item.media.close()
