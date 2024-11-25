"""
Slots
-----
This module defines some concrete implementations of slots.
"""

from __future__ import annotations

import asyncio
import re
from typing import Callable, Any, Awaitable, TYPE_CHECKING, Union, Dict
from typing_extensions import Annotated
import logging
from string import Formatter

from pydantic import model_validator, Field, field_serializer, field_validator

from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from chatsky.utils.devel.json_serialization import pickle_serializer, pickle_validator
from chatsky.slots.base_slots import (
    ExtractedSlot,
    BaseSlot,
    ValueSlot,
    SlotNotExtracted,
)

if TYPE_CHECKING:
    from chatsky.core import Context, Message


logger = logging.getLogger(__name__)


class KwargOnlyFormatter(Formatter):
    def get_value(self, key, args, kwargs):
        return super().get_value(str(key), args, kwargs)


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
    slots: Dict[str, Annotated[Union["ExtractedGroupSlot", "ExtractedValueSlot"], Field(union_mode="left_to_right")]]

    @property
    def __slot_extracted__(self) -> bool:
        return all([slot.__slot_extracted__ for slot in self.slots.values()])

    def __unset__(self):
        for child in self.slots.values():
            child.__unset__()

    # fill template here
    def __str__(self):
        if self.value_format is not None:
            return KwargOnlyFormatter().format(self.value_format, **self.slots)
        else:
            return str({key: str(value) for key, value in self.slots.items()})

    def update(self, old: "ExtractedGroupSlot"):
        """
        Rebase this extracted groups slot on top of another one.
        This is required to merge slot storage in-context
        with a potentially different slot configuration passed to pipeline.

        :param old: An instance of :py:class:`~.ExtractedGroupSlot` stored in-context.
            Extracted values will be transferred to this object.
        """
        for slot in old.slots:
            if slot in self.slots:
                new_slot = self.slots[slot]
                old_slot = old.slots[slot]
                if isinstance(new_slot, ExtractedGroupSlot) and isinstance(old_slot, ExtractedGroupSlot):
                    new_slot.update(old_slot)
                if isinstance(new_slot, ExtractedValueSlot) and isinstance(old_slot, ExtractedValueSlot):
                    self.slots[slot] = old_slot


class GroupSlot(BaseSlot, frozen=True):
    """
    Base class for :py:class:`~.RootSlot` and :py:class:`~.GroupSlot`.
    """

    value_format: str = None
    slots: Dict[str, Annotated[Union["GroupSlot", "ValueSlot"], Field(union_mode="left_to_right")]] = {}

    def __init__(self, **kwargs):  # supress unexpected argument warnings
        super().__init__(**kwargs)

    @model_validator(mode="after")
    def __check_slot_names__(self):
        """
        Slot names cannot contain dots.
        """
        for field in self.slots.keys():
            if "." in field:
                raise ValueError(f"Extra field name cannot contain dots: {field!r}")
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
        child_values = await asyncio.gather(*(child.get_value(ctx) for child in self.slots.values()))
        return ExtractedGroupSlot(
            value_format=self.value_format,
            slots={child_name: child_value for child_value, child_name in zip(child_values, self.slots.keys())},
        )

    def init_value(self) -> ExtractedGroupSlot:
        return ExtractedGroupSlot(slots={child_name: child.init_value() for child_name, child in self.slots.items()})


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
        request_text = ctx.last_request.text
        search = re.search(self.regexp, request_text)
        if search:
            return ExtractedGroupSlot(
                slots={
                    child_name: search.group(match_group)
                    for child_name, match_group in zip(self.groups.keys(), self.groups.values())
                }
            )
        else:
            return ExtractedGroupSlot(
                slots={
                    child_name: SlotNotExtracted(f"Failed to match pattern {self.regexp!r} in {request_text!r}.")
                    for child_name in self.groups.keys()
                }
            )

    def init_value(self) -> ExtractedGroupSlot:
        return ExtractedGroupSlot(
            slots={
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
