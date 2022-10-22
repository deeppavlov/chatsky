import logging
import sys
from typing import Union, Optional, List, Tuple, Any

from dff.core.engine.core import Context, Actor
from examples.utils import ConsoleFormatter


def run_auto_mode(
    actor: Actor,
    testing_dialog: List[Tuple[Any, Any]],
    logger: Optional[logging.Logger] = None
):
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = turn_handler(in_request, ctx, actor, true_out_response, logger)


def run_interactive_mode(actor: Actor, logger: Optional[logging.Logger] = None):
    ctx = {}
    while True:
        in_request = input(">>> ")
        _, ctx = turn_handler(in_request, ctx, actor, logger=logger)


# turn_handler - a function is made for the convenience of working with an actor
def turn_handler(
    in_request: str,
    ctx: Union[Context, str, dict],
    actor: Actor,
    true_out_response: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
):
    if logger is not None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(ConsoleFormatter())
        logger.addHandler(handler)
        logger.debug(f"USER: {in_request}")

    # Context.cast - gets an object type of [Context, str, dict] returns an object type of Context
    ctx = Context.cast(ctx)
    # Add in current context a next request of user
    ctx.add_request(in_request)
    # pass the context into actor and it returns updated context with actor response
    ctx = actor(ctx)
    # get last actor response from the context
    out_response = ctx.last_response
    # the next condition branching needs for testing
    if true_out_response is not None and true_out_response != out_response:
        msg = f"in_request={in_request} -> true_out_response != out_response: {true_out_response} != {out_response}"
        raise Exception(msg)
    elif logger is not None:
        logger.debug(f"BOT: {out_response}")
    else:
        print(f"<<< {out_response}")
    return out_response, ctx
