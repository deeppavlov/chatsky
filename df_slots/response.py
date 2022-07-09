"""
Response
---------------------------
This module is for functions that should be executed at the response stage.
They produce the response that will be ultimately given to the user.
"""
from typing import Union, Optional, List

from pydantic import validate_arguments

from df_generics import Response
from df_engine.core import Context, Actor

from .handlers import get_filled_template


@validate_arguments
def fill_template(template: Union[str, Response], slots: Optional[List[str]] = None):
    """
    Fill a template with slot values.
    Response should be an instance of :py:class:`~str` or of the :py:class:`~Response` class from df_generics add-on.

    Parameters
    ----------

    template: Union[str, :py:class:`~Response`]
        Template to fill. Names of slots to be used should be placed in curly braces: 'Username is {profile/username}'.
    slots: Optional[List[str]] = None
        Slot names to use. If this parameter is omitted, all slots will be used.
    """

    def fill_inner(ctx: Context, actor: Actor):
        if not isinstance(template, str) and not isinstance(template, Response):
            return template

        old_template = template if isinstance(template, str) else template.text
        new_template = get_filled_template(old_template, ctx, actor, slots)

        if isinstance(template, Response):
            template.text = new_template
            return template

        return new_template

    return fill_inner
