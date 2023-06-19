"""
Response
---------------------------
This module is for functions that should be executed at the response stage.
They produce the response that will be ultimately given to the user.
"""
from typing import Union, Optional, List

from pydantic import validate_arguments

from dff.script import Context, Message
from dff.pipeline import Pipeline

from .handlers import get_filled_template


@validate_arguments
def fill_template(template: Message, slots: Optional[List[str]] = None):
    """
    Fill a template with slot values.
    Response should be an instance of :py:class:`~str` or of the :py:class:`~Response` class from dff.connectors.messenger.generics add-on.

    Parameters
    ----------

    template:
        Template to fill. Names of slots to be used should be placed in curly braces: 'Username is {profile/username}'.
    slots: Optional[List[str]] = None
        Slot names to use. If this parameter is omitted, all slots will be used.
    """

    def fill_inner(ctx: Context, pipeline: Pipeline):
        new_template = template.copy()
        new_text = get_filled_template(template.text, ctx, pipeline, slots)
        new_template.text = new_text
        return new_template

    return fill_inner
