"""
Response
---------------------------
Slot-related Chatsky responses.
"""

from __future__ import annotations
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from chatsky.script import Context, Message
    from chatsky.pipeline import Pipeline


def filled_template(template: Message) -> Callable[[Context, Pipeline], Message]:
    """
    Fill template with slot values.
    The `text` attribute of the template message should be a format-string:
    e.g. "Your username is {profile.username}".

    For the example above, if ``profile.username`` slot has value "admin",
    it would return a copy of the message with the following text:
    "Your username is admin".

    :param template: Template message with a format-string text.
    """

    def fill_inner(ctx: Context, pipeline: Pipeline) -> Message:
        message = template.model_copy()
        new_text = ctx.framework_data.slot_manager.fill_template(template.text)
        message.text = new_text
        return message

    return fill_inner
