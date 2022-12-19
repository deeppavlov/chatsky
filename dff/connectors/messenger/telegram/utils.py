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

CallableParams = ParamSpec("CallableParams")
ReturnType = TypeVar("ReturnType")


def partialmethod(func: Callable[CallableParams, ReturnType], **part_kwargs) -> Callable[CallableParams, ReturnType]:
    """
    This function replaces the `partialmethod` implementation from functools.
    In contrast with the original class-based approach, it decorates the function, so we can use docstrings.
    """
    @wraps(func)
    def wrapper(self, *args: CallableParams.args, **kwargs: CallableParams.kwargs):
        kwargs = {**kwargs, **part_kwargs}
        return func(self, *args, **kwargs)

    return wrapper


def open_io(item: types.InputMedia):
    """Returns `InputMedia` with an opened file descriptor instead of path."""
    if isinstance(item.media, Path):
        item.media = item.media.open(mode="rb")
    return item


def close_io(item: types.InputMedia):
    """Closes an IO in an `InputMedia` object to perform the cleanup."""
    if isinstance(item.media, IOBase):
        item.media.close()
