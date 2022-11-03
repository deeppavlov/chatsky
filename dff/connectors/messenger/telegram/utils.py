from functools import wraps
from typing import Callable
from pathlib import Path
from io import IOBase
from copy import copy

from telebot import types
from dff.core.engine.core import Context


def set_state(ctx: Context, update: types.JsonDeserializable):
    """
    Updates a context with information from a new Telegram update (event) and returns this context.

    Parameters
    -----------

    ctx: :py:class:`~Context`
        Dialog Flow Engine context
    update: :py:class:`~types.JsonDeserializable`
        Any Telegram update, e. g. a message, a callback query or any other event

    """
    ctx.add_request(update.text if (hasattr(update, "text") and update.text) else "data")
    ctx.framework_states["TELEGRAM_CONNECTOR"]["data"] = update
    return ctx


def get_user_id(update: types.JsonDeserializable) -> str:
    """Extracts user ID from an update instance and casts it to a string"""
    assert hasattr(update, "from_user"), f"Received an invalid update object: {str(type(update))}."
    return str(update.from_user.id)


def get_content_type(update: types.JsonDeserializable) -> str:
    """Extracts content type from an update instance and casts it to a string"""
    assert hasattr(update, "content_type"), f"Received an invalid update object: {str(type(update))}."
    return str(update.content_type)


def get_text(update: types.JsonDeserializable) -> str:
    """Extracts text from a text update instance and casts it to a string"""
    assert hasattr(update, "text"), f"Received an invalid update object: {str(type(update))}."
    return str(update.text)


def get_initial_context(user_id: str):
    """
    Initialize a context with module-specific parameters.

    Parameters
    -----------

    user_id: str
        ID of the user from the update instance.

    """
    ctx = Context(id=user_id)
    ctx.framework_states.update({"TELEGRAM_CONNECTOR": {"keep_flag": True, "data": None}})
    return ctx


def partialmethod(func: Callable, **part_kwargs):
    """
    This function replaces the partialmethod implementation from functools.
    In contrast with the original class-based approach, it decorates the function, so we can use docstrings.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        return func(self, *args, **part_kwargs, **kwargs)

    if func.__doc__ is not None:
        doc: str = func.__doc__
        wrapper.__doc__ = doc.format(**part_kwargs)

    return wrapper


def open_io(item: types.InputMedia):
    """Returns a copy of InputMedia with an opened file descriptor instead of path."""
    copied_item = copy(item)
    if isinstance(copied_item.media, Path):
        copied_item.media = copied_item.media.open(mode="rb")
    return copied_item


def close_io(item: types.InputMedia):
    """Closes an IO in an InputMedia object to perform the cleanup."""
    if isinstance(item.media, IOBase):
        item.media.close()
