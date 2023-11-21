"""
Conditions
-----------
This module defines conditions for transitions between nodes.
"""
from typing import cast

from dff.script import Context
from dff.pipeline import Pipeline
from dff.messengers.telegram import TelegramMessage


def received_text(ctx: Context, _: Pipeline):
    """Return true if the last update from user contains text."""
    last_request = ctx.last_request

    return last_request.text is not None


def received_button_click(ctx: Context, _: Pipeline):
    """Return true if the last update from user is a button press."""
    if ctx.validation:  # Regular `Message` doesn't have `callback_query` field, so this fails during validation
        return False
    last_request = cast(TelegramMessage, ctx.last_request)

    return vars(last_request).get("callback_query") is not None
