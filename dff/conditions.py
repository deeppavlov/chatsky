from typing import Callable, Pattern, Union, Any, Iterable
import logging
import re

from pydantic import validate_arguments


from .core.actor import Actor
from .core.context import Context


logger = logging.getLogger(__name__)


@validate_arguments
def exact_match(match: Any, *args, **kwargs):
    def exact_match_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        request = ctx.last_request
        try:
            return match == request
        except Exception as exc:
            logger.error(f"Exception {exc} for {match=} and {request=}", exc_info=exc)

    return exact_match_condition_handler


@validate_arguments
def regexp(pattern: Union[Pattern, str], flags: Union[int, re.RegexFlag] = 0, *args, **kwargs):
    pattern = re.compile(pattern, flags)

    def regexp_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        request = ctx.last_request
        try:
            return bool(pattern.search(request))
        except Exception as exc:
            logger.error(f"Exception {exc} for {pattern=} and {request=}", exc_info=exc)

    return regexp_condition_handler


@validate_arguments
def reduce(iterable: Iterable, reduce_func: Callable = any, *args, **kwargs):
    iterable = list(iterable)
    for cond in iterable:
        if not isinstance(cond, Callable):
            raise Exception(f"{iterable=} has to consist of callable objects")

    def reduce_condition_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
        request = ctx.last_request
        try:
            return bool(reduce_func([cond(ctx, actor, *args, **kwargs) for cond in iterable]))
        except Exception as exc:
            logger.error(f"Exception {exc} for {iterable=}, {reduce_func=} and {request=}", exc_info=exc)

    return reduce_condition_handler
