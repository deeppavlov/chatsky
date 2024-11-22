"""
Base Slots
-----
This module defines base classes for slots.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from typing_extensions import TypeAlias
import logging
from functools import reduce
from string import Formatter

from pydantic import BaseModel

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


class KwargOnlyFormatter(Formatter):
    def get_value(self, key, args, kwargs):
        return super().get_value(str(key), args, kwargs)


class SlotNotExtracted(Exception):
    """This exception can be returned or raised by slot extractor if slot extraction is unsuccessful."""

    pass


class ExtractedSlot(BaseModel, ABC):
    """
    Represents value of an extracted slot.

    Instances of this class are managed by framework and
    are stored in :py:attr:`~chatsky.core.context.FrameworkData.slot_manager`.
    They can be accessed via the ``ctx.framework_data.slot_manager.get_extracted_slot`` method.
    """

    @property
    @abstractmethod
    def __slot_extracted__(self) -> bool:
        """Whether the slot is extracted."""
        raise NotImplementedError

    def __unset__(self):
        """Mark slot as not extracted and clear extracted data (except for default value)."""
        raise NotImplementedError

    @abstractmethod
    def __str__(self):
        """String representation is used to fill templates."""
        raise NotImplementedError


class BaseSlot(BaseModel, frozen=True):
    """
    BaseSlot is a base class for all slots.
    """

    @abstractmethod
    async def get_value(self, ctx: Context) -> ExtractedSlot:
        """
        Extract slot value from :py:class:`~.Context` and return an instance of :py:class:`~.ExtractedSlot`.
        """
        raise NotImplementedError

    @abstractmethod
    def init_value(self) -> ExtractedSlot:
        """
        Provide an initial value to fill slot storage with.
        """
        raise NotImplementedError
