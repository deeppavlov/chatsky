"""
Base Slots
-----
This module defines base classes for slots.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Union, Dict, Optional
from typing_extensions import Annotated
import logging
from string import Formatter

from pydantic import BaseModel, model_validator, Field, field_serializer, field_validator

from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from chatsky.utils.devel.json_serialization import pickle_serializer, pickle_validator

if TYPE_CHECKING:
    from chatsky.core import Context


logger = logging.getLogger(__name__)


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


class ExtractedValueSlot(ExtractedSlot):
    """Value extracted from :py:class:`~.ValueSlot`."""

    is_slot_extracted: bool
    extracted_value: Any
    default_value: Any = None

    @field_serializer("extracted_value", "default_value", when_used="json")
    def pickle_serialize_values(self, value):
        """
        Cast values to string via pickle.
        Allows storing arbitrary data in these fields when using context storages.
        """
        if value is not None:
            return pickle_serializer(value)
        return value

    @field_validator("extracted_value", "default_value", mode="before")
    @classmethod
    def pickle_validate_values(cls, value):
        """
        Restore values after being processed with
        :py:meth:`pickle_serialize_values`.
        """
        if value is not None:
            return pickle_validator(value)
        return value

    @property
    def __slot_extracted__(self) -> bool:
        return self.is_slot_extracted

    def __unset__(self):
        self.is_slot_extracted = False
        self.extracted_value = SlotNotExtracted("Slot manually unset.")

    @property
    def value(self):
        """Extracted value or the default value if the slot is not extracted."""
        return self.extracted_value if self.is_slot_extracted else self.default_value

    def __str__(self):
        return str(self.value)


class ExtractedGroupSlot(ExtractedSlot, extra="allow"):
    __pydantic_extra__: Dict[
        str, Annotated[Union["ExtractedGroupSlot", "ExtractedValueSlot"], Field(union_mode="left_to_right")]
    ]
    string_format: Optional[str] = None

    @property
    def __slot_extracted__(self) -> bool:
        return all([slot.__slot_extracted__ for slot in self.__pydantic_extra__.values()])

    def __unset__(self):
        for child in self.__pydantic_extra__.values():
            child.__unset__()

    # fill template here
    def __str__(self):
        if self.string_format is not None:
            return KwargOnlyFormatter().format(self.string_format, **self.__pydantic_extra__)
        else:
            return str({key: str(value) for key, value in self.__pydantic_extra__.items()})

    def update(self, old: "ExtractedGroupSlot"):
        """
        Rebase this extracted groups slot on top of another one.
        This is required to merge slot storage in-context
        with a potentially different slot configuration passed to pipeline.

        :param old: An instance of :py:class:`~.ExtractedGroupSlot` stored in-context.
            Extracted values will be transferred to this object.
        """
        for slot in old.__pydantic_extra__:
            if slot in self.__pydantic_extra__:
                new_slot = self.__pydantic_extra__[slot]
                old_slot = old.__pydantic_extra__[slot]
                if isinstance(new_slot, ExtractedGroupSlot) and isinstance(old_slot, ExtractedGroupSlot):
                    new_slot.update(old_slot)
                if isinstance(new_slot, ExtractedValueSlot) and isinstance(old_slot, ExtractedValueSlot):
                    self.__pydantic_extra__[slot] = old_slot


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


class GroupSlot(BaseSlot, extra="allow", frozen=True):
    """
    Base class for :py:class:`~.RootSlot` and :py:class:`~.GroupSlot`.
    """

    __pydantic_extra__: Dict[str, Annotated[Union["GroupSlot", "ValueSlot"], Field(union_mode="left_to_right")]]
    string_format: Optional[str] = None
    allow_partial_extraction: bool = False
    """If True, extraction returns only successfully extracted child slots."""

    def __init__(self, allow_partial_extraction=False, **kwargs):
        super().__init__(allow_partial_extraction=allow_partial_extraction, **kwargs)

    @model_validator(mode="before")
    @classmethod
    def __check_reserved_slot_names__(cls, data: Any):
        """
        Check that reserved names are used correctly and not taken by the user's slots.
        """
        if isinstance(data, dict):
            reserved_names = ["string_format", "allow_partial_extraction"]
            for name in reserved_names:
                if data.get(name) is not None:
                    if isinstance(data.get(name), BaseSlot):
                        raise TypeError(f"Slots cannot be named '{name}', it's a reserved name.")
        return data

    @model_validator(mode="after")
    def __check_extra_field_names__(self):
        """
        Extra field names cannot be dunder names or contain dots.
        """
        for field in self.__pydantic_extra__.keys():
            if "." in field:
                raise ValueError(f"Extra field name cannot contain dots: {field!r}")
            if field.startswith("__") and field.endswith("__"):
                raise ValueError(f"Extra field names cannot be dunder: {field!r}")
        return self

    def _flatten_group_slot(self, slot, parent_key=""):
        items = {}
        for key, value in slot.__pydantic_extra__.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, GroupSlot):
                items.update(self.__flatten_llm_group_slot(value, new_key))
            else:
                items[new_key] = value
        return items

    async def get_value(self, ctx: Context) -> ExtractedGroupSlot:
        child_values = await asyncio.gather(*(child.get_value(ctx) for child in self.__pydantic_extra__.values()))
        extracted_values = {}
        for child_value, child_name in zip(child_values, self.__pydantic_extra__.keys()):
            if child_value.__slot_extracted__ or not self.allow_partial_extraction:
                extracted_values[child_name] = child_value

        return ExtractedGroupSlot(string_format=self.string_format, **extracted_values)

    def init_value(self) -> ExtractedGroupSlot:
        return ExtractedGroupSlot(
            **{child_name: child.init_value() for child_name, child in self.__pydantic_extra__.items()}
        )
