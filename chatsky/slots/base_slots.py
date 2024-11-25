"""
Base Slots
-----
This module defines base classes for slots.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Union
import logging

from pydantic import BaseModel
from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async

if TYPE_CHECKING:
    from chatsky.core import Context
    from chatsky.slots.slots import ExtractedValueSlot


logger = logging.getLogger(__name__)


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


class ValueSlot(BaseSlot, frozen=True):
    """
    Value slot is a base class for all slots that are designed to extract concrete values.
    Subclass it, if you want to declare your own slot type.
    """

    default_value: Any = None

    @abstractmethod
    async def extract_value(self, ctx: Context) -> Union[Any, SlotNotExtracted]:
        """
        Return value extracted from context.

        Return :py:exc:`~.SlotNotExtracted` to mark extraction as unsuccessful.

        Raising exceptions is also allowed and will result in an unsuccessful extraction as well.
        """
        raise NotImplementedError

    async def get_value(self, ctx: Context) -> ExtractedValueSlot:
        """Wrapper for :py:meth:`~.ValueSlot.extract_value` to handle exceptions."""
        extracted_value = SlotNotExtracted("Caught an exit exception.")
        is_slot_extracted = False

        try:
            extracted_value = await wrap_sync_function_in_async(self.extract_value, ctx)
            is_slot_extracted = not isinstance(extracted_value, SlotNotExtracted)
        except Exception as error:
            logger.exception(f"Exception occurred during {self.__class__.__name__!r} extraction.", exc_info=error)
            extracted_value = error
        finally:
            if not is_slot_extracted:
                logger.debug(f"Slot {self.__class__.__name__!r} was not extracted: {extracted_value}")
            return ExtractedValueSlot.model_construct(
                is_slot_extracted=is_slot_extracted,
                extracted_value=extracted_value,
                default_value=self.default_value,
            )

    def init_value(self) -> ExtractedValueSlot:
        return ExtractedValueSlot.model_construct(
            is_slot_extracted=False,
            extracted_value=SlotNotExtracted("Initial slot extraction."),
            default_value=self.default_value,
        )
