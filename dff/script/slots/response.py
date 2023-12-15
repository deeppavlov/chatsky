"""
Response
---------------------------
This module is for functions that should be executed at the response stage.
They produce the response that will be ultimately given to the user.
"""
from typing import Callable, Optional, List

from pydantic import validate_call

from dff.script import Context, Message
from dff.pipeline import Pipeline

from .handlers import get_filled_template


@validate_call
def fill_template(template: Message, slots: Optional[List[str]] = None) -> Callable[[Context, Pipeline], Message]:
    """
    Fill a template with slot values.
    Response should be an instance of :py:class:`~.Message` class.

    :param template: Template message with placeholders enclosed by curly brackets {profile/username}'.
    :param slots: Slot names to use. If this parameter is omitted, all slots will be used.
    """

    def fill_inner(ctx: Context, pipeline: Pipeline) -> Message:
        new_template = template.model_copy()
        new_text = get_filled_template(template.text, ctx, pipeline, slots)
        new_template.text = new_text
        return new_template

    return fill_inner
