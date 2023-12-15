"""
Processing
---------------------------
This module encapsulates operations that can be done to slots during the processing stage.
"""
import logging
from typing import Awaitable, Optional, List, Callable

from pydantic import validate_call

from dff.script import Context
from dff.pipeline import Pipeline

from .handlers import get_filled_template, extract as extract_handler, unset as unset_handler

logger = logging.getLogger(__name__)


@validate_call
def extract(slots: Optional[List[str]]) -> Callable[[Context, Pipeline], Awaitable[None]]:
    """
    Extract slots from a specified list.

    :param slots: List of slot names to extract.
        Names of slots inside groups should be prefixed with group names, separated by '/': profile/username.
    """

    async def extract_inner(ctx: Context, pipeline: Pipeline) -> None:
        _ = extract_handler(ctx, pipeline, slots)
        return

    return extract_inner


@validate_call
def unset(slots: Optional[List[str]] = None) -> Callable[[Context, Pipeline], None]:
    def unset_inner(ctx: Context, pipeline: Pipeline) -> None:
        unset_handler(ctx, pipeline, slots)
        return

    return unset_inner


@validate_call
def fill_template(slots: Optional[List[str]] = None) -> Callable[[Context, Pipeline], None]:
    """
    Fill the response template in the current node.
    Response should be an instance of :py:class:`~.Message`.
    Names of slots to be used should be placed in curly braces: 'Username is {profile/username}'.

    :param slots: Slot names to use. If this parameter is omitted, all slots will be used.
    """

    def fill_inner(ctx: Context, pipeline: Pipeline) -> None:
        # get current node response
        response = ctx.current_node.response
        if callable(response):
            response = response(ctx, pipeline)

        new_text = get_filled_template(response.text, ctx, pipeline, slots)

        response.text = new_text
        ctx.current_node.response = response

        return

    return fill_inner
