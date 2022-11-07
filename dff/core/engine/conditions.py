"""
Conditions
---------------------------
Conditions are one of the most important components of the dialog graph,
which determine the possibility of transition from one node of the graph to another node.
This is a standard set of engine conditions.
"""
from typing import Callable, Pattern, Union, Any, List, Optional
import logging
import re

from pydantic import validate_arguments

from .core.types import NodeLabel2Type

from .core.actor import Actor
from .core.context import Context

logger = logging.getLogger(__name__)


@validate_arguments
def exact_match(match: Any, *args, **kwargs) -> Callable:
    """Returns function handler.
    This handler returns True only if the last user phrase is exactly
    the same as the :py:const:`match <any>.`

    :param match:
        the variable of the same type as  :py:class:`~dff.core.engine.core.context.last_request`
    :type match: Any
    """

    def exact_match_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        request = ctx.last_request
        return match == request

    return exact_match_condition_handler


@validate_arguments
def regexp(pattern: Union[str, Pattern], flags: Union[int, re.RegexFlag] = 0, *args, **kwargs) -> Callable:
    """Returns function handler.
    This handler returns True only if the last user phrase contains
    :py:const:`pattern <Union[str, Pattern]>` with
    :py:const:`flags <Union[int, re.RegexFlag]>`.

    :param pattern:
        the RegExp pattern
    :type pattern: Union[str, Pattern]
    :param flags:
        flags for this pattern
        Defaults to 0
    :type flags: Union[int, re.RegexFlag]
    """
    pattern = re.compile(pattern, flags)

    def regexp_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        request = ctx.last_request
        if isinstance(request, str):
            return bool(pattern.search(request))
        else:
            logger.error(f"request has to be str type, but got request={request}")
            return False

    return regexp_condition_handler


@validate_arguments
def check_cond_seq(cond_seq: list):
    """Checks if the list consists only of Callables.

    :param cond_seq:
        list of conditions to check
    :type cond_seq: list
    """
    for cond in cond_seq:
        if not isinstance(cond, Callable):
            raise TypeError(f"{cond_seq} has to consist of callable objects")


_any = any
""" _any is an alias for any. """
_all = all
""" _all is an alias for all. """


@validate_arguments
def aggregate(cond_seq: list, aggregate_func: Callable = _any, *args, **kwargs) -> Callable:
    """Aggregates multiple functions into one by using aggregating function.
    Returns function handler.

    :param cond_seq:
        list of conditions to check
    :type cond_seq: list
    :param aggregate_func:
        function to aggregate conditions
        Defaults to :py:func:`._any`
    :type aggregate_func: Callable
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
def any(cond_seq: list, *args, **kwargs) -> Callable:
    """Function that returns function handler. This handler returns True
    if any function from the list is True.

    :param cond_seq:
        list of conditions to check
    :type cond_seq: list
    """
    _agg = aggregate(cond_seq, _any)

    def any_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return _agg(ctx, actor, *args, **kwargs)

    return any_condition_handler


@validate_arguments
def all(cond_seq: list, *args, **kwargs) -> Callable:
    """Function that returns function handler. This handler returns True only
    if all functions from the list are True.

    :param cond_seq:
        list of conditions to check
    :type cond_seq: list
    """
    _agg = aggregate(cond_seq, _all)

    def all_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return _agg(ctx, actor, *args, **kwargs)

    return all_condition_handler


@validate_arguments
def negation(condition: Callable, *args, **kwargs) -> Callable:
    """Returns function handler.
    This handler returns negation of the :py:func:`~condition`: False
    if :py:func:`~condition` holds True and True otherwise

    :param condition:
        any :py:func:`~condition`
    :type condition: Callable
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
) -> Callable:
    """
    Function returns condition handler.
    This handler returns True if any label from
    last :py:const:`last_n_indices <int>` context labels is in
    the :py:const:`flow_labels <List[str]>` list or in
    the :py:const:`labels ~dff.core.engine.core.types.NodeLabel2Type` list.

    :param flow_labels:
        list of labels to check.Every label has type `str`. Is empty if not set.
    :type flow_labels: Optional[List[str]]
    :param labels:
        list of labels that correspond to the nodes. Is empty is not set.
    :type labels: Optional[List[NodeLabel2Type]]
    :param last_n_indices:
        number of last utterances to check.
    :type last_n_indices: int
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
def true(*args, **kwargs) -> Callable:
    """Returns function handler. This handler always returns True."""

    def true_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return True

    return true_handler


@validate_arguments
def false(*args, **kwargs) -> Callable:
    """Returns function handler. This handler always returns False."""

    def false_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return False

    return false_handler


# aliases
agg = aggregate
""":py:func:`~agg` is an alias for :py:func:`~aggregate`."""
neg = negation
""":py:func:`~neg` is an alias for :py:func:`~negation`."""
