"""
Conditions
----------
Conditions are one of the most important components of the dialog graph.
They determine the possibility of transition from one node of the graph to another.
The conditions are used to specify when a particular transition should occur, based on certain criteria.
This module contains a standard set of scripting conditions that can be used to control the flow of a conversation.
These conditions can be used to check the current context, the user's input,
or other factors that may affect the conversation flow.
"""
import asyncio
from typing import Pattern, Union, List, Optional
import logging
import re
from functools import cached_property

from pydantic import Field, computed_field

from chatsky.core import BaseCondition, Context
from chatsky.core.message import Message, MessageInitTypes, CallbackQuery
from chatsky.core.node_label import AbsoluteNodeLabel, AbsoluteNodeLabelInitTypes

logger = logging.getLogger(__name__)


class ExactMatch(BaseCondition):
    """
    Return function handler. This handler returns `True` only if the last user phrase
    is the same `Message` as the `match`.
    If `skip_none` the handler will not compare `None` fields of `match`.

    :param match: A `Message` variable to compare user request with.
        Can also accept `str`, which will be converted into a `Message` with its text field equal to `match`.
    :param skip_none: Whether fields should be compared if they are `None` in :py:const:`match`.
    """
    match: Message
    skip_none: bool = True

    def __init__(self, match: MessageInitTypes, *, skip_none=True):
        super().__init__(match=match, skip_none=skip_none)

    async def func(self, ctx: Context) -> bool:
        request = ctx.last_request
        for field in self.match.model_fields:
            match_value = self.match.__getattribute__(field)
            if self.skip_none and match_value is None:
                continue
            if field in request.model_fields.keys():
                if request.__getattribute__(field) != self.match.__getattribute__(field):
                    return False
            else:
                return False
        return True


class HasText(BaseCondition):
    """
    Return function handler. This handler returns `True` only if the last user phrase
    contains the phrase specified in `text`.

    :param text: A `str` variable to look for within the user request.
    """
    text: str

    def __init__(self, text):
        super().__init__(text=text)

    async def func(self, ctx: Context) -> bool:
        request = ctx.last_request
        if request.text is None:
            return False
        return self.text in request.text


class Regexp(BaseCondition):
    """
    Return function handler. This handler returns `True` only if the last user phrase contains
    `pattern` with `flags`.

    :param pattern: The `RegExp` pattern.
    :param flags: Flags for this pattern. Defaults to 0.
    """
    pattern: Union[str, Pattern]
    flags: Union[int, re.RegexFlag] = 0

    def __init__(self, pattern, *, flags=0):
        super().__init__(pattern=pattern, flags=flags)

    @computed_field
    @cached_property
    def re_object(self) -> Pattern:
        return re.compile(self.pattern, self.flags)

    async def func(self, ctx: Context) -> bool:
        request = ctx.last_request
        if request.text is None:
            return False
        return bool(self.re_object.search(request.text))


class Any(BaseCondition):
    """
    Return function handler. This handler returns `True`
    if any function from the list is `True`.

    :param cond_seq: List of conditions to check.
    """
    conditions: List[BaseCondition]

    def __init__(self, *conditions):
        super().__init__(conditions=list(conditions))

    async def func(self, ctx: Context) -> bool:
        return any(await asyncio.gather(*(cnd(ctx) for cnd in self.conditions)))


class All(BaseCondition):
    """
    Return function handler. This handler returns `True` only
    if all functions from the list are `True`.

    :param cond_seq: List of conditions to check.
    """
    conditions: List[BaseCondition]

    def __init__(self, *conditions):
        super().__init__(conditions=list(conditions))

    async def func(self, ctx: Context) -> bool:
        return all(await asyncio.gather(*(cnd(ctx) for cnd in self.conditions)))


class Negation(BaseCondition):
    """
    Return function handler. This handler returns negation of the :py:func:`~condition`: `False`
    if :py:func:`~condition` holds `True` and returns `True` otherwise.

    :param condition: Any :py:func:`~condition`.
    """
    condition: BaseCondition

    def __init__(self, condition):
        super().__init__(condition=condition)

    async def func(self, ctx: Context) -> bool:
        result = await self.condition.wrapped_call(ctx)
        return result is not True


Not = Negation
"""
:py:func:`~Not` is an alias for :py:func:`~Negation`.
"""


class CheckLastLabels(BaseCondition):
    """
    Return condition handler. This handler returns `True` if any label from
    last `last_n_indices` context labels is in
    the `flow_labels` list or in
    the `labels` list.

    :param flow_labels: List of labels to check. Every label has type `str`. Empty if not set.
    :param labels: List of labels corresponding to the nodes. Empty if not set.
    :param last_n_indices: Number of last utterances to check.
    """
    flow_labels: List[str] = Field(default_factory=list)
    labels: List[AbsoluteNodeLabel] = Field(default_factory=list)
    last_n_indices: int = Field(default=1, ge=1)

    def __init__(self, *, flow_labels=None, labels: Optional[List[AbsoluteNodeLabelInitTypes]] = None, last_n_indices=1):
        if flow_labels is None:
            flow_labels = []
        if labels is None:
            labels = []
        super().__init__(flow_labels=flow_labels, labels=labels, last_n_indices=last_n_indices)

    async def func(self, ctx: Context) -> bool:
        labels = list(ctx.labels.values())[-self.last_n_indices:]
        for label in labels:
            if label.flow_name in self.flow_labels or label in self.labels:
                return True
        return False


class HasCallbackQuery(BaseCondition):
    """
    Condition that checks if :py:attr:`~.CallbackQuery.query_string`
    of the last message matches `query_string`.

    :param query_string: The expected query string to compare with.
    :return: The callback query comparator function.
    """
    query_string: str

    def __init__(self, query_string):
        super().__init__(query_string=query_string)

    async def func(self, ctx: Context) -> bool:
        last_request = ctx.last_request
        if last_request.attachments is None:
            return False
        for attachment in last_request.attachments:
            if isinstance(attachment, CallbackQuery):
                if attachment.query_string == self.query_string:
                    return True
        return False
