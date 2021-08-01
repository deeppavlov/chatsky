from typing import Callable

from dff.core.context import Context


def deep_copy_condition_handler(condition: Callable, ctx: Context, actor: "Actor", *args, **kwargs):
    return condition(ctx.copy(deep=True), actor.copy(deep=True), *args, **kwargs)
