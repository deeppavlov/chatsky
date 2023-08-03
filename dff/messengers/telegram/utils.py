"""
Utils
------
This module contains utilities for connecting to Telegram.
"""
from typing import Union, Iterable
from contextlib import contextmanager
from pathlib import Path
from io import IOBase

from telebot import types


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
