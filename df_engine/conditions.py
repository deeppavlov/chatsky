"""
Conditions
---------------------------
Conditions are one of the most important components of the dialog graph,
which determine the possibility of transition from one node of the graph to another node.
This is a standard set of engine conditions.
"""
from typing import Callable, Pattern, Union, Any
import logging
import re

from pydantic import validate_arguments

from df_engine.core.types import NodeLabel2Type

from .core.actor import Actor
from .core.context import Context

logger = logging.getLogger(__name__)


@validate_arguments
def exact_match(match: Any, *args, **kwargs) -> Callable:
    """
    Returns function handler.
    This handler returns True only if the last user phrase is exactly
    the same as the :py:const:`match <any>.`

    Parameters
    ----------

    match: Any
        the variable of the same type as  :py:class:`~df_engine.core.context.last_request`
    """

    def exact_match_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        request = ctx.last_request
        return match == request

    return exact_match_condition_handler


@validate_arguments
def regexp(pattern: Union[str, Pattern], flags: Union[int, re.RegexFlag] = 0, *args, **kwargs) -> Callable:
    """
    Returns function handler.
    This handler returns True only if the last user phrase contains
    :py:const:`pattern <Union[str, Pattern]>` with
    :py:const:`flags <Union[int, re.RegexFlag]>`.

    Parameters
    ----------

    `pattern`: Union[str, Pattern]
        the RegExp pattern

    flags: Union[int, re.RegexFlag] = 0
         flags for this pattern
    """
    pattern = re.compile(pattern, flags)

    def regexp_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        request = ctx.last_request
        return bool(pattern.search(request))

    return regexp_condition_handler


@validate_arguments
def check_cond_seq(cond_seq: list):
    """
    Checks if the list consists only of Callables.

    Parameters
    ----------

    cond_seq: list
        list of conditions to check
    """
    for cond in cond_seq:
        if not isinstance(cond, Callable):
            raise TypeError(f"{cond_seq=} has to consist of callable objects")


_any = any
""" _any is an alias for any. """
_all = all
""" _all is an alias for all. """


@validate_arguments
def aggregate(cond_seq: list, aggregate_func: Callable = _any, *args, **kwargs) -> Callable:
    """
    Aggregates multiple functions into one by using agregating function.
    Returns function handler.

    Parameters
    ----------

    cond_seq: list
        list of conditions to check
    aggregate_func: Callable = _any
        function to aggregate conditions
    """
    check_cond_seq(cond_seq)

    def aggregate_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        try:
            return bool(aggregate_func([cond(ctx, actor, *args, **kwargs) for cond in cond_seq]))
        except Exception as exc:
            logger.error(f"Exception {exc} for {cond_seq=}, {aggregate_func=} and {ctx.last_request=}", exc_info=exc)

    return aggregate_condition_handler


@validate_arguments
def any(cond_seq: list, *args, **kwargs) -> Callable:
    """
    Function that returns function handler. This handler returns True
    if any function from the list is True.

    Parameters
    ----------
    cond_seq: list
        list of conditions to check
    """
    _agg = aggregate(cond_seq, _any)

    def any_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return _agg(ctx, actor, *args, **kwargs)

    return any_condition_handler


@validate_arguments
def all(cond_seq: list, *args, **kwargs) -> Callable:
    """
    Function that returns function handler. This handler returns True only
    if all functions from the list are True.

    Parameters
    ----------
    cond_seq: list
        list of conditions to check
    """
    _agg = aggregate(cond_seq, _all)

    def all_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return _agg(ctx, actor, *args, **kwargs)

    return all_condition_handler


@validate_arguments
def negation(condition: Callable, *args, **kwargs) -> Callable:
    """
    Returns function handler.
    This handler returns negation of the :py:func:`~condition`: False
    if :py:func:`~condition` holds True and True otherwise

    Parameters
    ----------
    condition: Callable
        any :py:func:`~condition`
    """

    def negation_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return not condition(ctx, actor, *args, **kwargs)

    return negation_condition_handler


@validate_arguments
def has_last_labels(
    flow_labels: list[str] = [], labels: list[NodeLabel2Type] = [], last_n_indexes: int = 1, *args, **kwargs
) -> Callable:
    """
    Function returns condition handler.
    This handler returns True if any label from
    last :py:const:`last_n_indexes <int>`context labels is in
    the :py:const:`flow_labels <list[str]>` list or in
    the :py:const:`labels ~df_engine.core.types.NodeLabel2Type` list.

    Parameters
    ----------
    flow_labels: list
        list of labels to check.Every label has type `str`. Is empty if not set.
    labels: list[:py:const:`~df_engine.core.types.NodeLabel2Type`]
        list of labels that correspond to the nodes. Is empty is not set.
    last_n_indexes: int
        number of last utterances to check.
    """

    def has_last_labels_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        label = list(ctx.labels.values())[-last_n_indexes:]
        for label in list(ctx.labels.values())[-last_n_indexes:]:
            label = label if label else (None, None)
            if label[0] in flow_labels or label in labels:
                return True
        return False

    return has_last_labels_condition_handler


@validate_arguments
def true(*args, **kwargs) -> Callable:
    """
    Returns function handler. This handler always returns True.
    """

    def true_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return True

    return true_handler


@validate_arguments
def false(*args, **kwargs) -> Callable:
    """
    Returns function handler. This handler always returns False.
    """

    def false_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        return False

    return false_handler


# aliases
agg = aggregate
""" :py:func:`~agg` is an alias for :py:func:`~aggregate`. """
neg = negation
""" :py:func:`~neg` is an alias for :py:func:`~negation`. """
