# from typing import ForwardRef
from typing import Callable

from pydantic import validate_arguments, BaseModel

from .core.context import Context


Actor = BaseModel  # ForwardRef("Actor")


@validate_arguments()
def deep_copy_condition_handler(condition: Callable, ctx: Context, actor: Actor, *args, **kwargs):
    return condition(ctx.copy(deep=True), actor.copy(deep=True), *args, **kwargs)
