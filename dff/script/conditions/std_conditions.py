"""
Conditions
---------------------------
Conditions are one of the most important components of the dialog graph,
which determine the possibility of transition from one node of the graph to another.
This is a standard set of scripting conditions.
"""
from typing import Callable, Pattern, Union, Any, List, Optional
import logging
import re

from pydantic import validate_arguments

from dff.script import NodeLabel2Type, Actor, Context, Message

logger = logging.getLogger(__name__)


@validate_arguments
def exact_match(match: Message, skip_none: bool = True, *args, **kwargs) -> Callable[..., bool]:
    """
    Returns function handler. This handler returns `True` only if the last user phrase
    is the same Message as the :py:const:`match`.
    If :py:const:`skip_none` the handler will not compare None fields of :py:const:`match`.

    :param match: A Message variable to compare user request with.
    :param skip_none: Whether fields should be compared if they are None in :py:const:`match`.
    """

    def exact_match_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        request = ctx.last_request
        if request is None:
            return False
        for field in match.__fields__:
            match_value = match.__getattribute__(field)
            if skip_none and match_value is None:
                continue
            if field in request.__fields__.keys():
                if request.__getattribute__(field) != match.__getattribute__(field):
                    return False
            else:
                return False
        return True

    return exact_match_condition_handler


@validate_arguments
def regexp(
    pattern: Union[str, Pattern], flags: Union[int, re.RegexFlag] = 0, *args, **kwargs
) -> Callable[[Context, Actor, Any, Any], bool]:
    """
    Returns function handler. This handler returns `True` only if the last user phrase contains
    :py:const:`pattern <Union[str, Pattern]>` with :py:const:`flags <Union[int, re.RegexFlag]>`.

    :param pattern: The `RegExp` pattern.
    :param flags: Flags for this pattern. Defaults to 0.
    """
    pattern = re.compile(pattern, flags)

    def regexp_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        request = ctx.last_request
        if isinstance(request, Message):
            if request.text is None:
                return False
            return bool(pattern.search(request.text))
        else:
            logger.error(f"request has to be str type, but got request={request}")
            return False

    return regexp_condition_handler


@validate_arguments
def check_cond_seq(cond_seq: list):
    """
    Checks if the list consists only of Callables.

    :param cond_seq: List of conditions to check.
    """
    for cond in cond_seq:
        if not isinstance(cond, Callable):
            raise TypeError(f"{cond_seq} has to consist of callable objects")


_any = any
"""
_any is an alias for any.
"""
_all = all
"""
_all is an alias for all.
"""


@validate_arguments
def aggregate(
    cond_seq: list, aggregate_func: Callable = _any, *args, **kwargs
) -> Callable[[Context, Actor, Any, Any], bool]:
    """
    Aggregates multiple functions into one by using aggregating function.

    :param cond_seq: List of conditions to check.
    :param aggregate_func: Function to aggregate conditions. Defaults to :py:func:`_any`.
    """
    check_cond_seq(cond_seq)

    def aggregate_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        try:
            return bool(aggregate_func([cond(ctx, actor, *args, **kwargs) for cond in cond_seq]))
        except Exception as exc:
            logger.error(f"Exception {exc} for {cond_seq}, {aggregate_func} and {ctx.last_request}", exc_info=exc)
            return False

    return aggregate_condition_handler


@validate_arguments
def any(cond_seq: list, *args, **kwargs) -> Callable[[Context, Actor, Any, Any], bool]:
    """
    Returns function handler. This handler returns `True`
    if any function from the list is `True`.

    :param cond_seq: List of conditions to check.
    """
    _agg = aggregate(cond_seq, _any)

    def any_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return _agg(ctx, actor, *args, **kwargs)

    return any_condition_handler


@validate_arguments
def all(cond_seq: list, *args, **kwargs) -> Callable[[Context, Actor, Any, Any], bool]:
    """
    Returns function handler. This handler returns `True` only
    if all functions from the list are `True`.

    :param cond_seq: List of conditions to check.
    """
    _agg = aggregate(cond_seq, _all)

    def all_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return _agg(ctx, actor, *args, **kwargs)

    return all_condition_handler


@validate_arguments
def negation(condition: Callable, *args, **kwargs) -> Callable[[Context, Actor, Any, Any], bool]:
    """
    Returns function handler. This handler returns negation of the :py:func:`~condition`: `False`
    if :py:func:`~condition` holds `True` and returns `True` otherwise.

    :param condition: Any :py:func:`~condition`.
    """

    def negation_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return not condition(ctx, actor, *args, **kwargs)

    return negation_condition_handler


@validate_arguments
def has_last_labels(
    flow_labels: Optional[List[str]] = None,
    labels: Optional[List[NodeLabel2Type]] = None,
    last_n_indices: int = 1,
    *args,
    **kwargs,
) -> Callable[[Context, Actor, Any, Any], bool]:
    """
    Returns condition handler. This handler returns `True` if any label from
    last :py:const:`last_n_indices` context labels is in
    the :py:const:`flow_labels` list or in
    the :py:const:`~dff.script.NodeLabel2Type` list.

    :param flow_labels: List of labels to check. Every label has type `str`. Empty if not set.
    :param labels: List of labels corresponding to the nodes. Empty if not set.
    :param last_n_indices: Number of last utterances to check.
    """
    flow_labels = [] if flow_labels is None else flow_labels
    labels = [] if labels is None else labels

    def has_last_labels_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        label = list(ctx.labels.values())[-last_n_indices:]
        for label in list(ctx.labels.values())[-last_n_indices:]:
            label = label if label else (None, None)
            if label[0] in flow_labels or label in labels:
                return True
        return False

    return has_last_labels_condition_handler


@validate_arguments
def true(*args, **kwargs) -> Callable[[Context, Actor, Any, Any], bool]:
    """
    Returns function handler. This handler always returns `True`.
    """

    def true_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return True

    return true_handler


@validate_arguments
def false(*args, **kwargs) -> Callable[[Context, Actor, Any, Any], bool]:
    """
    Returns function handler. This handler always returns `False`.
    """

    def false_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return False

    return false_handler


# aliases
agg = aggregate
"""
:py:func:`~agg` is an alias for :py:func:`~aggregate`.
:rtype:
"""
neg = negation
"""
:py:func:`~neg` is an alias for :py:func:`~negation`.
:rtype:
"""
