"""
Conditions
---------------------------
Provides slot-related conditions.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from chatsky.script import Context
    from chatsky.slots.slots import SlotName
    from chatsky.pipeline import Pipeline


def slots_extracted(*slots: SlotName, mode: Literal["any", "all"] = "all"):
    """
    Conditions that checks if slots are extracted.

    :param slots: Names for slots that need to be checked.
    :param mode: Whether to check if all slots are extracted or any slot is extracted.
    """

    def check_slot_state(ctx: Context, pipeline: Pipeline) -> bool:
        manager = ctx.framework_data.slot_manager
        if mode == "all":
            return all(manager.is_slot_extracted(slot) for slot in slots)
        elif mode == "any":
            return any(manager.is_slot_extracted(slot) for slot in slots)
        raise ValueError(f"{mode!r} not in ['any', 'all'].")

    return check_slot_state
