"""
Slot Manager
-----
This module defines the SlotManager class, facilitating slot management for Pipeline.
"""

from __future__ import annotations

from typing_extensions import TypeAlias
from typing import Union, TYPE_CHECKING, Optional
import logging

from functools import reduce

from pydantic import BaseModel, Field

from chatsky.slots.base_slots import (
    ExtractedSlot,
    BaseSlot,
    ExtractedValueSlot,
    ExtractedGroupSlot,
    GroupSlot,
    KwargOnlyFormatter,
)

if TYPE_CHECKING:
    from chatsky.core import Context

logger = logging.getLogger(__name__)

SlotName: TypeAlias = str
"""
A string to identify slots.

Top-level slots are identified by their key in a :py:class:`~.GroupSlot`.

E.g.

.. code:: python

    GroupSlot(
        user=RegexpSlot(),
        password=FunctionSlot,
    )

Has two slots with names "user" and "password".

For nested group slots use dots to separate names:

.. code:: python

    GroupSlot(
        user=GroupSlot(
            name=FunctionSlot,
            password=FunctionSlot,
        )
    )

Has two slots with names "user.name" and "user.password".
"""


def recursive_getattr(obj, slot_name: SlotName):
    def two_arg_getattr(__o, name):
        # pydantic handles exception when accessing a non-existing extra-field on its own
        # return None by default to avoid that
        return getattr(__o, name, None)

    return reduce(two_arg_getattr, [obj, *slot_name.split(".")])


def recursive_setattr(obj, slot_name: SlotName, value):
    parent_slot, _, slot = slot_name.rpartition(".")

    if parent_slot:
        setattr(recursive_getattr(obj, parent_slot), slot, value)
    else:
        setattr(obj, slot, value)


class SlotManager(BaseModel):
    """
    Provides API for managing slots.

    An instance of this class can be accessed via ``ctx.framework_data.slot_manager``.
    """

    slot_storage: ExtractedGroupSlot = Field(default_factory=ExtractedGroupSlot)
    """Slot storage. Stored inside ctx.framework_data."""
    root_slot: GroupSlot = Field(default_factory=GroupSlot, exclude=True)
    """Slot configuration passed during pipeline initialization."""

    def set_root_slot(self, root_slot: GroupSlot):
        """
        Set root_slot configuration from pipeline.
        Update extracted slots with the new configuration:

        New slots are added with their :py:meth:`~.BaseSlot.init_value`.
        Old extracted slot values are preserved only if their configuration did not change.
        That is if they are still present in the config and if their fundamental type did not change
        (i.e. `GroupSlot` did not turn into a `ValueSlot` or vice versa).

        This method is called by pipeline and is not supposed to be used otherwise.
        """
        self.root_slot = root_slot
        new_slot_storage = root_slot.init_value()
        new_slot_storage.update(self.slot_storage)
        self.slot_storage = new_slot_storage

    def get_slot(self, slot_name: SlotName) -> BaseSlot:
        """
        Get slot configuration from the slot name.

        :raises KeyError: If the slot with the specified name does not exist.
        """
        slot = recursive_getattr(self.root_slot, slot_name)
        if isinstance(slot, BaseSlot):
            return slot
        raise KeyError(f"Could not find slot {slot_name!r}.")

    async def extract_slot(self, slot_name: SlotName, ctx: Context, save_on_failure: bool) -> None:
        """
        Extract slot `slot_name` and store extracted value in `slot_storage`.

        :raises KeyError: If the slot with the specified name does not exist.

        :param slot_name: Name of the slot to extract.
        :param ctx: Context.
        :param save_on_failure: Whether to store the value only if it is successfully extracted.
        """
        slot = self.get_slot(slot_name)
        value = await slot.get_value(ctx)

        if value.__slot_extracted__ or save_on_failure is False:
            recursive_setattr(self.slot_storage, slot_name, value)

    async def extract_all(self, ctx: Context):
        """
        Extract all slots from slot configuration `root_slot` and set `slot_storage` to the extracted value.
        """
        self.slot_storage = await self.root_slot.get_value(ctx)

    def get_extracted_slot(self, slot_name: SlotName) -> Union[ExtractedValueSlot, ExtractedGroupSlot]:
        """
        Retrieve extracted value from `slot_storage`.

        :raises KeyError: If the slot with the specified name does not exist.
        """
        slot = recursive_getattr(self.slot_storage, slot_name)
        if isinstance(slot, ExtractedSlot):
            return slot
        raise KeyError(f"Could not find slot {slot_name!r}.")

    def is_slot_extracted(self, slot_name: str) -> bool:
        """
        Return if the specified slot is extracted.

        :raises KeyError: If the slot with the specified name does not exist.
        """
        return self.get_extracted_slot(slot_name).__slot_extracted__

    def all_slots_extracted(self) -> bool:
        """
        Return if all slots are extracted.
        """
        return self.slot_storage.__slot_extracted__

    def unset_slot(self, slot_name: SlotName) -> None:
        """
        Mark specified slot as not extracted and clear extracted value.

        :raises KeyError: If the slot with the specified name does not exist.
        """
        self.get_extracted_slot(slot_name).__unset__()

    def unset_all_slots(self) -> None:
        """
        Mark all slots as not extracted and clear all extracted values.
        """
        self.slot_storage.__unset__()

    def fill_template(self, template: str) -> Optional[str]:
        """
        Fill `template` string with extracted slot values and return a formatted string
        or None if an exception has occurred while trying to fill template.

        `template` should be a format-string:

        E.g. "Your username is {profile.username}".

        For the example above, if ``profile.username`` slot has value "admin",
        it would return the following text:
        "Your username is admin".
        """
        try:
            return KwargOnlyFormatter().format(template, **dict(self.slot_storage.slots.items()))
        except Exception as exc:
            logger.exception("An exception occurred during template filling.", exc_info=exc)
            return None
