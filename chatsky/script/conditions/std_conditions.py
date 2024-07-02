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

from typing import Callable, Pattern, Union, List, Optional
import logging
import re

from pydantic import validate_call

from chatsky.pipeline import Pipeline
from chatsky.script import NodeLabel2Type, Context, Message
from chatsky.script.core.message import CallbackQuery

logger = logging.getLogger(__name__)


@validate_call
def exact_match(match: Union[str, Message], skip_none: bool = True) -> Callable[[Context, Pipeline], bool]:
    """
    Return function handler. This handler returns `True` only if the last user phrase
    is the same `Message` as the `match`.
    If `skip_none` the handler will not compare `None` fields of `match`.

    :param match: A `Message` variable to compare user request with.
        Can also accept `str`, which will be converted into a `Message` with its text field equal to `match`.
    :param skip_none: Whether fields should be compared if they are `None` in :py:const:`match`.
    """

    def exact_match_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
        request = ctx.last_request
        nonlocal match
        if isinstance(match, str):
            match = Message(text=match)
        if request is None:
            return False
        for field in match.model_fields:
            match_value = match.__getattribute__(field)
            if skip_none and match_value is None:
                continue
            if field in request.model_fields.keys():
                if request.__getattribute__(field) != match.__getattribute__(field):
                    return False
            else:
                return False
        return True

    return exact_match_condition_handler


@validate_call
def has_text(text: str) -> Callable[[Context, Pipeline], bool]:
    """
    Return function handler. This handler returns `True` only if the last user phrase
    contains the phrase specified in `text`.

    :param text: A `str` variable to look for within the user request.
    """

    def has_text_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
        request = ctx.last_request
        return text in request.text

    return has_text_condition_handler


@validate_call
def regexp(pattern: Union[str, Pattern], flags: Union[int, re.RegexFlag] = 0) -> Callable[[Context, Pipeline], bool]:
    """
    Return function handler. This handler returns `True` only if the last user phrase contains
    `pattern` with `flags`.

    :param pattern: The `RegExp` pattern.
    :param flags: Flags for this pattern. Defaults to 0.
    """
    pattern = re.compile(pattern, flags)

    def regexp_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
        request = ctx.last_request
        if isinstance(request, Message):
            if request.text is None:
                return False
            return bool(pattern.search(request.text))
        else:
            logger.error(f"request has to be str type, but got request={request}")
            return False

    return regexp_condition_handler


@validate_call
def check_cond_seq(cond_seq: list):
    """
    Check if the list consists only of Callables.

    :param cond_seq: List of conditions to check.
    """
    for cond in cond_seq:
        if not callable(cond):
            raise TypeError(f"{cond_seq} has to consist of callable objects")


_any = any
"""
_any is an alias for any.
"""
_all = all
"""
_all is an alias for all.
"""


@validate_call
def aggregate(cond_seq: list, aggregate_func: Callable = _any) -> Callable[[Context, Pipeline], bool]:
    """
    Aggregate multiple functions into one by using aggregating function.

    :param cond_seq: List of conditions to check.
    :param aggregate_func: Function to aggregate conditions. Defaults to :py:func:`_any`.
    """
    check_cond_seq(cond_seq)

    def aggregate_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
        try:
            return bool(aggregate_func([cond(ctx, pipeline) for cond in cond_seq]))
        except Exception as exc:
            logger.error(f"Exception {exc} for {cond_seq}, {aggregate_func} and {ctx.last_request}", exc_info=exc)
            return False

    return aggregate_condition_handler


@validate_call
def any(cond_seq: list) -> Callable[[Context, Pipeline], bool]:
    """
    Return function handler. This handler returns `True`
    if any function from the list is `True`.

    :param cond_seq: List of conditions to check.
    """
    _agg = aggregate(cond_seq, _any)

    def any_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
        return _agg(ctx, pipeline)

    return any_condition_handler


@validate_call
def all(cond_seq: list) -> Callable[[Context, Pipeline], bool]:
    """
    Return function handler. This handler returns `True` only
    if all functions from the list are `True`.

    :param cond_seq: List of conditions to check.
    """
    _agg = aggregate(cond_seq, _all)

    def all_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
        return _agg(ctx, pipeline)

    return all_condition_handler


@validate_call
def negation(condition: Callable) -> Callable[[Context, Pipeline], bool]:
    """
    Return function handler. This handler returns negation of the :py:func:`~condition`: `False`
    if :py:func:`~condition` holds `True` and returns `True` otherwise.

    :param condition: Any :py:func:`~condition`.
    """

    def negation_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
        return not condition(ctx, pipeline)

    return negation_condition_handler


@validate_call
def has_last_labels(
    flow_labels: Optional[List[str]] = None,
    labels: Optional[List[NodeLabel2Type]] = None,
    last_n_indices: int = 1,
) -> Callable[[Context, Pipeline], bool]:
    """
    Return condition handler. This handler returns `True` if any label from
    last `last_n_indices` context labels is in
    the `flow_labels` list or in
    the `labels` list.

    :param flow_labels: List of labels to check. Every label has type `str`. Empty if not set.
    :param labels: List of labels corresponding to the nodes. Empty if not set.
    :param last_n_indices: Number of last utterances to check.
    """
    # todo: rewrite docs & function itself
    flow_labels = [] if flow_labels is None else flow_labels
    labels = [] if labels is None else labels

    def has_last_labels_condition_handler(ctx: Context, pipeline: Pipeline) -> bool:
        label = list(ctx.labels.values())[-last_n_indices:]
        for label in list(ctx.labels.values())[-last_n_indices:]:
            label = label if label else (None, None)
            if label[0] in flow_labels or label in labels:
                return True
        return False

    return has_last_labels_condition_handler


@validate_call
def true() -> Callable[[Context, Pipeline], bool]:
    """
    Return function handler. This handler always returns `True`.
    """

    def true_handler(ctx: Context, pipeline: Pipeline) -> bool:
        return True

    return true_handler


@validate_call
def false() -> Callable[[Context, Pipeline], bool]:
    """
    Return function handler. This handler always returns `False`.
    """

    def false_handler(ctx: Context, pipeline: Pipeline) -> bool:
        return False

    return false_handler


# aliases
agg = aggregate
"""
:py:func:`~agg` is an alias for :py:func:`~aggregate`.
"""
neg = negation
"""
:py:func:`~neg` is an alias for :py:func:`~negation`.
"""


def has_callback_query(expected_query_string: str) -> Callable[[Context, Pipeline], bool]:
    """
    Condition that checks if :py:attr:`~.CallbackQuery.query_string`
    of the last message matches `expected_query_string`.

    :param expected_query_string: The expected query string to compare with.
    :return: The callback query comparator function.
    """

    def has_callback_query_handler(ctx: Context, _: Pipeline) -> bool:
        last_request = ctx.last_request
        if last_request is None or last_request.attachments is None:
            return False
        return CallbackQuery(query_string=expected_query_string) in last_request.attachments

    return has_callback_query_handler
