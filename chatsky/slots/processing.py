"""
Processing
---------------------------
This module provides wrappers for :py:class:`~chatsky.slots.slots.SlotManager`'s API.
"""

from __future__ import annotations

import logging
from typing import Awaitable, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from chatsky.slots.slots import SlotName
    from chatsky.script import Context
    from chatsky.pipeline import Pipeline

logger = logging.getLogger(__name__)


def extract(*slots: SlotName) -> Callable[[Context, Pipeline], Awaitable[None]]:
    """
    Extract slots listed slots.
    This will override all slots even if they are already extracted.

    :param slots: List of slot names to extract.
    """

    async def inner(ctx: Context, pipeline: Pipeline) -> None:
        manager = ctx.framework_data.slot_manager
        for slot in slots:  # todo: maybe gather
            await manager.extract_slot(slot, ctx, pipeline)

    return inner


def extract_all():
    """
    Extract all slots defined in the pipeline.
    """

    async def inner(ctx: Context, pipeline: Pipeline):
        manager = ctx.framework_data.slot_manager
        await manager.extract_all(ctx, pipeline)

    return inner


def unset(*slots: SlotName) -> Callable[[Context, Pipeline], None]:
    """
    Mark specified slots as not extracted and clear extracted values.

    :param slots: List of slot names to extract.
    """

    def unset_inner(ctx: Context, pipeline: Pipeline) -> None:
        manager = ctx.framework_data.slot_manager
        for slot in slots:
            manager.unset_slot(slot)

    return unset_inner


def unset_all():
    """
    Mark all slots as not extracted and clear all extracted values.
    """

    def inner(ctx: Context, pipeline: Pipeline):
        manager = ctx.framework_data.slot_manager
        manager.unset_all_slots()

    return inner


def fill_template() -> Callable[[Context, Pipeline], None]:
    """
    Fill the response template in the current node.

    Response message of the current node should be a format-string: e.g. "Your username is {profile.username}".
    """

    def inner(ctx: Context, pipeline: Pipeline) -> None:
        manager = ctx.framework_data.slot_manager
        # get current node response
        response = ctx.current_node.response

        if response is None:
            return

        if callable(response):
            response = response(ctx, pipeline)

        new_text = manager.fill_template(response.text)

        response.text = new_text
        ctx.current_node.response = response

    return inner
