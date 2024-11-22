"""
Slot Conditions
---------------------------
Provides slot-related conditions.
"""

from __future__ import annotations
from typing import Literal, List, Any

from chatsky.core import Context, BaseCondition
from chatsky.slots.base_slots import SlotName


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


class SlotValueEquals(BaseCondition):
    """
    Check if :py:attr:`.slot_name`'s extracted value is equal to a given value.

    :raises KeyError: If the slot with the specified name does not exist.
    """

    slot_name: SlotName
    """
    Name of the slot that needs to be checked.
    """
    value: Any
    """
    The value which the slot's extracted value is supposed to be checked against.
    """

    def __init__(self, slot_name: SlotName, value: Any):
        super().__init__(slot_name=slot_name, value=value)

    async def call(self, ctx: Context) -> bool:
        manager = ctx.framework_data.slot_manager
        return manager.get_extracted_slot(self.slot_name).self.value == self.value
