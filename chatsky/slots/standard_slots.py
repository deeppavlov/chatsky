"""
Standard Slots
--------------
This module defines some concrete implementations of slots.
"""

from __future__ import annotations

import re
from re import Pattern
from typing import Callable, Any, Awaitable, TYPE_CHECKING, Union, Dict, Optional
import logging

from pydantic import Field, model_validator
from typing_extensions import Annotated

from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from chatsky.slots.base_slots import (
    SlotNotExtracted,
    ExtractedValueSlot,
    ExtractedGroupSlot,
    ValueSlot,
    GroupSlot,
)

if TYPE_CHECKING:
    from chatsky.core import Context, Message


logger = logging.getLogger(__name__)


class RegexpSlot(ValueSlot, frozen=True):
    """
    RegexpSlot is a slot type that extracts its value using a regular expression.
    You can pass a compiled or a non-compiled pattern to the `regexp` argument.
    If you want to extract a particular group, but not the full match,
    change the `match_group_idx` parameter.
    """

    regexp: str
    "The regexp to search for in ctx.last_request.text"
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


class RegexpGroupSlot(GroupSlot, extra="forbid", frozen=True):
    """
    A slot type that applies a regex pattern once to extract values for
    multiple child slots. Accepts a `regexp` pattern and a `groups` dictionary
    mapping slot names to group indexes. Improves efficiency by performing a
    single regex search for all specified groups, thus reducing the amount
    of calls to your model.
    """

    # Parent fields repeated for Pydantic issues
    __pydantic_extra__: Dict[str, Annotated[Union["GroupSlot", "ValueSlot"], Field(union_mode="left_to_right")]]
    string_format: Optional[str] = None
    allow_partial_extraction: bool = False
    "Unlike in `GroupSlot` this field has no effect in this class. If a slot doesn't"

    regexp: Pattern
    "The regexp to search for in ctx.last_request.text"
    groups: dict[str, int]
    "A dictionary mapping slot names to match_group indexes."
    default_values: dict[str, Any] = Field(default_factory=dict)
    "A dictionary with default values for each slot name in case a slot's extraction fails."

    @model_validator(mode="after")
    def validate_groups(self):
        for elem in self.groups.values():
            if elem > self.regexp.groups:
                raise ValueError("Requested group number is too high, there aren't that many capture groups!")
            if elem < 0:
                raise ValueError("Requested capture group number cannot be negative.")
        return self

    def __init__(self, regexp: Union[str, Pattern], groups: dict[str, int], default_values: dict[str, Any] = None,
                 string_format: str = None, flags: int = 0):
        init_dict = {
            "regexp": re.compile(regexp, flags),
            "groups": groups,
            "default_values": default_values,
            "string_format": string_format,
        }
        empty_fields = set()
        for k, v in init_dict.items():
            if k not in self.model_fields:
                raise NotImplementedError("Init method contains a field not in model fields.")
            if v is None:
                empty_fields.add(k)
        for field in empty_fields:
            del init_dict[field]
        super().__init__(**init_dict)

    async def get_value(self, ctx: Context) -> ExtractedGroupSlot:
        request_text = ctx.last_request.text
        search = re.search(self.regexp, request_text)
        if search:
            return ExtractedGroupSlot(
                string_format=self.string_format,
                **{
                    child_name: ExtractedValueSlot.model_construct(
                        is_slot_extracted=True,
                        extracted_value=search.group(match_group),
                    )
                    for child_name, match_group in zip(self.groups.keys(), self.groups.values())
                },
            )
        else:
            return ExtractedGroupSlot(
                string_format=self.string_format,
                **{
                    child_name: ExtractedValueSlot.model_construct(
                        is_slot_extracted=False,
                        extracted_value=SlotNotExtracted(
                            f"Failed to match pattern {self.regexp!r} in {request_text!r}."
                        ),
                        default_value=self.default_values.get(child_name, None),
                    )
                    for child_name in self.groups.keys()
                },
            )

    def init_value(self) -> ExtractedGroupSlot:
        return ExtractedGroupSlot(
            string_format=self.string_format,
            **{
                child_name: RegexpSlot(regexp=self.regexp, match_group_id=match_group).init_value()
                for child_name, match_group in self.groups.items()
            },
        )


class FunctionSlot(ValueSlot, frozen=True):
    """
    A simpler version of :py:class:`~.ValueSlot`.

    Uses a user-defined `func` to extract slot value from the :py:attr:`~.Context.last_request` Message.
    """

    func: Callable[[Message], Union[Awaitable[Union[Any, SlotNotExtracted]], Any, SlotNotExtracted]]

    async def extract_value(self, ctx: Context) -> Union[Any, SlotNotExtracted]:
        return await wrap_sync_function_in_async(self.func, ctx.last_request)
