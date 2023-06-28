"""
Processing
---------------------------
This module encapsulates operations that can be done to slots during the processing stage.
"""
import logging
from typing import Optional, List, Callable

from pydantic import validate_arguments

from dff.script import Context, Message
from dff.pipeline import Pipeline

from .handlers import get_filled_template, extract as extract_handler, unset as unset_handler

logger = logging.getLogger(__name__)


@validate_arguments
def extract(slots: Optional[List[str]]) -> Callable:
    """
    Extract slots from a specified list.

    Parameters
    ----------

    slots: Optional[List[str]]
        List of slot names to extract.
        Names of slots inside groups should be prefixed with group names, separated by '/': profile/username.
    """

    def extract_inner(ctx: Context, pipeline: Pipeline) -> Context:
        _ = extract_handler(ctx, pipeline, slots)
        return ctx

    return extract_inner


@validate_arguments
def unset(slots: Optional[List[str]] = None):
    def unset_inner(ctx: Context, pipeline: Pipeline) -> Context:
        unset_handler(ctx, pipeline, slots)
        return ctx

    return unset_inner


@validate_arguments
def fill_template(slots: Optional[List[str]] = None):
    """
    Fill the response template in the current node.
    Response should be an instance of :py:class:`~str` or of the :py:class:`~Response` class from dff.connectors.messenger.generics add-on.
    Names of slots to be used should be placed in curly braces: 'Username is {profile/username}'.

    Parameters
    ----------

    slots: Optional[List[str]] = None
        Slot names to use. If this parameter is omitted, all slots will be used.
    """

    def fill_inner(ctx: Context, pipeline: Pipeline) -> Message:

        # get current node response
        response = ctx.current_node.response
        if callable(response):
            response = response(ctx, pipeline)

        new_text = get_filled_template(response.text, ctx, pipeline, slots)

        response.text = new_text
        ctx.current_node.response = response

        return ctx

    return fill_inner
