"""
Utils
------
This module contains utilities for connecting to Telegram.
"""
from functools import wraps
from typing import Callable, Union, Iterable
from typing_extensions import ParamSpec
from contextlib import contextmanager
from pathlib import Path
from io import IOBase

try:
    from typing import TypeVar
except ImportError:
    from typing_extensions import TypeVar

from telebot import types

CallableParams = ParamSpec("CallableParams")
ReturnType = TypeVar("ReturnType")


def partialmethod(func: Callable[CallableParams, ReturnType], **part_kwargs) -> Callable[CallableParams, ReturnType]:
    """
    This function replaces the `partialmethod` implementation from functools.
    In contrast with the original class-based approach, it decorates the function, so we can use docstrings.
    """

    @wraps(func)
    def wrapper(self, *args: CallableParams.args, **kwargs: CallableParams.kwargs) -> ReturnType:
        new_kwargs = {**kwargs, **part_kwargs}
        return func(self, *args, **new_kwargs)

    return wrapper


def open_io(item: types.InputMedia):
    """
    Returns `InputMedia` with an opened file descriptor instead of path.

    :param item: InputMedia object.
    """
    if isinstance(item.media, Path):
        item.media = item.media.open(mode="rb")
    return item


def close_io(item: types.InputMedia):
    """
    Closes an IO in an `InputMedia` object to perform the cleanup.

    :param item: InputMedia object.
    """
    if isinstance(item.media, IOBase):
        item.media.close()


@contextmanager
def batch_open_io(item: Union[types.InputMedia, Iterable[types.InputMedia]]):
    """
    Context manager that controls the state of file descriptors inside `InputMedia`.
    Can be used both for single objects and collections.

    :param item: InputMedia objects that contain file descriptors.
    """
    if isinstance(item, Iterable):
        resources = list(map(open_io, item))
    else:
        resources = open_io(item)
    try:
        yield resources
    finally:
        if isinstance(resources, Iterable):
            for resource in resources:
                close_io(resource)
        else:
            close_io(resources)
