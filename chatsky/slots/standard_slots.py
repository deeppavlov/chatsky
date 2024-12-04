"""
Slots
-----
This module defines some concrete implementations of slots.
"""

from __future__ import annotations

import re
from typing import Callable, Any, Awaitable, TYPE_CHECKING, Union, Dict, Optional
import logging

from pydantic import Field
from typing_extensions import Annotated

from chatsky.utils.devel.async_helpers import wrap_sync_function_in_async
from chatsky.slots.base_slots import (
    SlotNotExtracted,
    ExtractedValueSlot,
    ExtractedGroupSlot,
    ValueSlot,
    BaseSlot,
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

    regexp: str
    groups: dict[str, int]
    "A dictionary mapping slot names to match_group indexes."
    default_values: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **kwargs):  # supress unexpected argument warnings
        super().__init__(**kwargs)

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
