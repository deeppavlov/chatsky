from typing import Callable
from flows import Flows
from context import Context


def deep_copy_condition_handler(condition: Callable, ctx: Context, flows: Flows, *args, **kwargs):
    return condition(ctx.copy(deep=True), flows.copy(deep=True), *args, **kwargs)
