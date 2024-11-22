"""
Slots
-----
This module defines some concrete implementations of slots.
"""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from typing import Callable, Any, Awaitable, TYPE_CHECKING, Union, Optional, Dict
from typing_extensions import TypeAlias, Annotated
import logging
from functools import reduce
from string import Formatter

from pydantic import BaseModel, model_validator, Field, field_serializer, field_validator

from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from chatsky.utils.devel.json_serialization import pickle_serializer, pickle_validator
from chatsky.slots.base_slots import ExtractedSlot, BaseSlot, SlotNotExtracted, KwargOnlyFormatter

if TYPE_CHECKING:
    from chatsky.core import Context, Message


logger = logging.getLogger(__name__)


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
    value_format: str = None
    __pydantic_extra__: Dict[
        str, Annotated[Union["ExtractedGroupSlot", "ExtractedValueSlot"], Field(union_mode="left_to_right")]
    ]

    @property
    def __slot_extracted__(self) -> bool:
        return all([slot.__slot_extracted__ for slot in self.__pydantic_extra__.values()])

    def __unset__(self):
        for child in self.__pydantic_extra__.values():
            child.__unset__()

    # fill template here
    def __str__(self):
        if self.value_format is not None:
            # return str({key: Kwargs.format() for key, value in self.__pydantic_extra__.items()})
            return KwargOnlyFormatter().format(self.value_format, **self.__pydantic_extra__)
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

    value_format: str = None
    __pydantic_extra__: Dict[str, Annotated[Union["GroupSlot", "ValueSlot"], Field(union_mode="left_to_right")]]

    def __init__(self, **kwargs):  # supress unexpected argument warnings
        super().__init__(**kwargs)

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

    async def get_value(self, ctx: Context) -> ExtractedGroupSlot:
        child_values = await asyncio.gather(*(child.get_value(ctx) for child in self.__pydantic_extra__.values()))
        return ExtractedGroupSlot(
            value_format=self.value_format,
            **{
                child_name: child_value
                for child_value, child_name in zip(child_values, self.__pydantic_extra__.keys())
            }
        )

    def init_value(self) -> ExtractedGroupSlot:
        return ExtractedGroupSlot(
            **{child_name: child.init_value() for child_name, child in self.__pydantic_extra__.items()}
        )


class RegexpSlot(ValueSlot, frozen=True):
    """
    RegexpSlot is a slot type that extracts its value using a regular expression.
    You can pass a compiled or a non-compiled pattern to the `regexp` argument.
    If you want to extract a particular group, but not the full match,
    change the `match_group_idx` parameter.
    """

    regexp: str
    match_group_idx: int = 0
    "Index of the group to match."

    async def extract_value(self, ctx: Context) -> Union[str, SlotNotExtracted]:
        request_text = ctx.last_request.text
        search = re.search(self.regexp, request_text)
        return (
            search.group(self.match_group_idx)
            if search
            else SlotNotExtracted(f"Failed to match pattern {self.regexp!r} in {request_text!r}.")
        )


# TODO: Change class and method descriptions.
class RegexpGroupSlot(GroupSlot, frozen=True):
    """
    RegexpGroupSlot is semantically equal to a GroupSlot of RegexpSlots.
    You can pass a compiled or a non-compiled pattern to the `regexp` argument.
    If you want to extract a particular group, but not the full match,
    change the `match_group_idx` parameter.
    """

    regexp: str
    groups: dict[str, int]
    "Index of the group to match."

    def __init__(self, **kwargs):  # supress unexpected argument warnings
        super().__init__(**kwargs)

    async def get_value(self, ctx: Context) -> ExtractedGroupSlot:
        child_values = await asyncio.gather(
            *(
                RegexpSlot(regexp=self.regexp, match_group_id=match_group).get_value(ctx)
                for match_group in self.groups.values()
            )
        )
        return ExtractedGroupSlot(
            **{child_name: child_value for child_value, child_name in zip(child_values, self.groups.keys())}
        )

    def init_value(self) -> ExtractedGroupSlot:
        return ExtractedGroupSlot(
            **{
                child_name: RegexpSlot(regexp=self.regexp, match_group_id=match_group).init_value()
                for child_name, match_group in self.groups.items()
            }
        )


class FunctionSlot(ValueSlot, frozen=True):
    """
    A simpler version of :py:class:`~.ValueSlot`.

    Uses a user-defined `func` to extract slot value from the :py:attr:`~.Context.last_request` Message.
    """

    func: Callable[[Message], Union[Awaitable[Union[Any, SlotNotExtracted]], Any, SlotNotExtracted]]

    async def extract_value(self, ctx: Context) -> Union[Any, SlotNotExtracted]:
        return await wrap_sync_function_in_async(self.func, ctx.last_request)

