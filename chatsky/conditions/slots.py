"""
Slot Conditions
---------------------------
Provides slot-related conditions.
"""

from __future__ import annotations
from typing import Literal, List

from chatsky.core import Context, BaseCondition
from chatsky.slots.slots import SlotName


class SlotsExtracted(BaseCondition):
    """
    Check if :py:attr:`.slots` are extracted.

    :param mode: Whether to check if all slots are extracted or any slot is extracted.
    """

    slots: List[SlotName]
    """
    Names of the slots that need to be checked.
    """
    mode: Literal["any", "all"] = "all"
    """
    Whether to check if all slots are extracted or any slot is extracted.
    """

    def __init__(self, *slots: SlotName, mode: Literal["any", "all"] = "all"):
        super().__init__(slots=slots, mode=mode)

    async def call(self, ctx: Context) -> bool:
        manager = ctx.framework_data.slot_manager
        if self.mode == "all":
            return all(manager.is_slot_extracted(slot) for slot in self.slots)
        elif self.mode == "any":
            return any(manager.is_slot_extracted(slot) for slot in self.slots)


class GroupSlotsExtracted(BaseCondition):
    """
    Check if :py:attr:`.slots` are extracted.

    :param mode: Whether to check if all slots are extracted or any slot is extracted.
    """

    slots: List[SlotName]
    """
    Names of the slots that need to be checked.
    """
    required: List[SlotName]
    """
    If required slots are extracted condition will return true despite non-required slots being extracted or not.
    By default set to `["all"]` that sets all slots to required.
    """

    def __init__(self, *slots: SlotName, required: List[str] = ["all"]):
        super().__init__(slots=slots, required=required)

    async def call(self, ctx: Context) -> bool:
        manager = ctx.framework_data.slot_manager
        if self.required == ["all"]:
            return all(manager.is_slot_extracted(slot) for slot in self.slots)
        else:
            return all(manager.is_slot_extracted(slot) for slot in self.required)
