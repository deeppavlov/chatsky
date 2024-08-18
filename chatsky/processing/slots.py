"""
Processing
---------------------------
This module provides wrappers for :py:class:`~chatsky.slots.slots.SlotManager`'s API.
"""
import asyncio
import logging
from typing import List

from chatsky.slots.slots import SlotName
from chatsky.core import Context, BaseProcessing
from chatsky.responses.slots import FilledTemplate

logger = logging.getLogger(__name__)


class Extract(BaseProcessing):
    """
    Extract slots listed slots.
    This will override all slots even if they are already extracted.

    :param slots: List of slot names to extract.
    """
    slots: List[SlotName]

    def __init__(self, *slots: SlotName):
        super().__init__(slots=slots)

    async def func(self, ctx: Context):
        manager = ctx.framework_data.slot_manager
        results = await asyncio.gather(*(manager.extract_slot(slot, ctx) for slot in self.slots), return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.exception("An exception occurred during slot extraction.", exc_info=result)


class ExtractAll(BaseProcessing):
    """
    Extract all slots defined in the pipeline.
    """

    async def func(self, ctx: Context):
        manager = ctx.framework_data.slot_manager
        await manager.extract_all(ctx)


class Unset(BaseProcessing):
    """
    Mark specified slots as not extracted and clear extracted values.

    :param slots: List of slot names to extract.
    """
    slots: List[SlotName]

    def __init__(self, *slots: SlotName):
        super().__init__(slots=slots)

    async def func(self, ctx: Context):
        manager = ctx.framework_data.slot_manager
        for slot in self.slots:
            try:
                manager.unset_slot(slot)
            except Exception as exc:
                logger.exception("An exception occurred during slot resetting.", exc_info=exc)


class UnsetAll(BaseProcessing):
    """
    Mark all slots as not extracted and clear all extracted values.
    """

    async def func(self, ctx: Context):
        manager = ctx.framework_data.slot_manager
        manager.unset_all_slots()


class FillTemplate(BaseProcessing):
    """
    Fill the response template in the current node.

    Response message of the current node should be a format-string: e.g. "Your username is {profile.username}".
    """

    async def func(self, ctx: Context):
        response = ctx.current_node.response

        if response is None:
            return

        ctx.current_node.response = FilledTemplate(template=response)
