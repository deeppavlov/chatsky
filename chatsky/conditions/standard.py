"""
Standard Conditions
-------------------
This module provides basic conditions.

- :py:class:`.Any`, :py:class:`.All` and :py:class:`.Negation` are meta-conditions.
- :py:class:`.HasText`, :py:class:`.Regexp`, :py:class:`.HasCallbackQuery` are last-request-based conditions.
- :py:class:`.CheckLastLabels` is a label-based condition.
"""

import asyncio
from typing import Literal, Pattern, Sequence, Union, List, cast
import logging
import re
from functools import cached_property

from pydantic import Field, computed_field, field_validator, model_validator

from chatsky.core import BaseCondition, Context
from chatsky.core.message import Message, MessageInitTypes, CallbackQuery
from chatsky.core.node_label import AbsoluteNodeLabel, AbsoluteNodeLabelInitTypes

logger = logging.getLogger(__name__)


class ExactMatch(BaseCondition):
    """
    Check if :py:attr:`~.Context.last_request` matches :py:attr:`.match`.

    If :py:attr:`.skip_fields`, will allow skip matching the fields of :py:attr:`.match`.
    """

    match: MessageInitTypes
    """
    Message to compare last request with.

    Is initialized according to :py:data:`~.MessageInitTypes`.
    """
    skip_fields: Sequence[Literal["text", "attachments", "annotations", "misc", "origin"] | str] = Field(default=["origin"])
    """
    Listed fields should not be compared in :py:attr:`.match`.
    """

    @field_validator("match", mode="before")
    @classmethod
    def validate_match(cls, value):
        return Message.model_validate(value)
    
    @model_validator(mode="after")
    def skip_fields_validator(self):
        extra_fields = set(self.skip_fields) - set(self.match.__dict__.keys())
        if extra_fields:
            raise ValueError(extra_fields)
        else:
            return self

    async def call(self, ctx: Context) -> bool:
        match: Message = cast(Message, self.match)

        request = ctx.last_request
        for field in match.__dict__:
            if field in self.skip_fields:
                continue
            match_value = match.__getattribute__(field)
            if field in request.__dict__:
                if request.__getattribute__(field) != match_value:
                    return False
            else:
                return False
        return True


class HasText(BaseCondition):
    """
    Check if the :py:attr:`~.Message.text` attribute of :py:attr:`~.Context.last_request`
    contains :py:attr:`.text`.
    """

    text: str
    """
    Text to search for in the last request.
    """

    async def call(self, ctx: Context) -> bool:
        request = ctx.last_request
        if request.text is None:
            return False
        return self.text in request.text


class Regexp(BaseCondition):
    """
    Check if the :py:attr:`~.Message.text` attribute of :py:attr:`~.Context.last_request`
    contains :py:attr:`.pattern`.
    """

    pattern: Union[str, Pattern]
    """
    The `RegExp` pattern to search for in the last request.
    """
    flags: Union[int, re.RegexFlag] = 0
    """
    Flags to pass to ``re.compile``.
    """

    @computed_field
    @cached_property
    def re_object(self) -> Pattern:
        """Compiled pattern."""
        return re.compile(self.pattern, self.flags)

    async def call(self, ctx: Context) -> bool:
        request = ctx.last_request
        if request.text is None:
            return False
        return bool(self.re_object.search(request.text))


class Any(BaseCondition):
    """
    Check if any condition from the :py:attr:`.conditions` list is True.
    """

    conditions: List[BaseCondition]
    """
    List of conditions.
    """

    async def call(self, ctx: Context) -> bool:
        return any(await asyncio.gather(*(cnd.is_true(ctx) for cnd in self.conditions)))


class All(BaseCondition):
    """
    Check if all conditions from the :py:attr:`.conditions` list is True.
    """

    conditions: List[BaseCondition]
    """
    List of conditions.
    """

    async def call(self, ctx: Context) -> bool:
        return all(await asyncio.gather(*(cnd.is_true(ctx) for cnd in self.conditions)))


class Negation(BaseCondition):
    """
    Return the negation of the result of :py:attr:`~.Negation.condition`.
    """

    condition: BaseCondition
    """
    Condition to negate.
    """

    async def call(self, ctx: Context) -> bool:
        return not await self.condition.is_true(ctx)


Not = Negation
"""
:py:class:`.Not` is an alias for :py:class:`.Negation`.
"""


class CheckLastLabels(BaseCondition):
    """
    Check if any label in the last :py:attr:`.last_n_indices` of :py:attr:`.Context.labels` is in
    :py:attr:`.labels` or if its :py:attr:`~.AbsoluteNodeLabel.flow_name` is in :py:attr:`.flow_labels`.
    """

    flow_labels: List[str] = Field(default_factory=list)
    """
    List of flow names to find in the last labels.
    """
    labels: List[AbsoluteNodeLabelInitTypes] = Field(default_factory=list)
    """
    List of labels to find in the last labels.

    Is initialized according to :py:data:`~.AbsoluteNodeLabelInitTypes`.
    """
    last_n_indices: int = Field(default=1, ge=1)
    """
    Number of labels to check.
    """

    @field_validator("labels", mode="before")
    @classmethod
    def validate_labels(cls, labels):
        return [AbsoluteNodeLabel.model_validate(label) for label in labels]

    async def call(self, ctx: Context) -> bool:
        labels = await ctx.labels.get(ctx.labels.keys()[-self.last_n_indices :])  # noqa: E203

        for label in labels:
            if label.flow_name in self.flow_labels or label in self.labels:
                return True
        return False


class HasCallbackQuery(BaseCondition):
    """
    Check if :py:attr:`~.Context.last_request` contains a :py:class:`.CallbackQuery` attachment
    with :py:attr:`.CallbackQuery.query_string` matching :py:attr:`.HasCallbackQuery.query_string`.
    """

    query_string: str
    """
    Query string to find in last request's attachments.
    """

    async def call(self, ctx: Context) -> bool:
        last_request = ctx.last_request
        if last_request.attachments is None:
            return False
        for attachment in last_request.attachments:
            if isinstance(attachment, CallbackQuery):
                if attachment.query_string == self.query_string:
                    return True
        return False
