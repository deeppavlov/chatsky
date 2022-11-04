"""
6. Context serialization
========================
"""

import logging

from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE
from dff.core.engine.core import Context, Actor
import dff.core.engine.conditions as cnd
from dff._example_utils.index import run_interactive_mode, run_actor, is_in_notebook

logger = logging.getLogger(__name__)


def response_handler(ctx: Context, actor: Actor, *args, **kwargs) -> str:
    return f"answer {len(ctx.requests)}"


# a dialog script
script = {
    "flow_start": {"node_start": {RESPONSE: response_handler, TRANSITIONS: {("flow_start", "node_start"): cnd.true()}}}
}


actor = Actor(script, start_label=("flow_start", "node_start"))


testing_dialog = [("hi", "answer 1"), ("how are you?", "answer 2"), ("ok", "answer 3"), ("good", "answer 4")]


def run_auto_mode():
    ctx = {}
    iterator = iter(testing_dialog)
    in_request, true_out_response = next(iterator)
    # pass as empty context
    _, ctx = run_actor(in_request, ctx, actor, true_out_response, logger=logger)
    # serialize context to json str
    ctx = ctx.json()
    if isinstance(ctx, str):
        logging.info("context serialized to json str")
    else:
        raise Exception(f"ctx={ctx} has to be serialized to json string")
    in_request, true_out_response = next(iterator)
    _, ctx = run_actor(in_request, ctx, actor, true_out_response, logger=logger)
    # serialize context to dict
    ctx = ctx.dict()
    if isinstance(ctx, dict):
        logging.info("context serialized to dict")
    else:
        raise Exception(f"ctx={ctx} has to be serialized to dict")
    in_request, true_out_response = next(iterator)
    _, ctx = run_actor(in_request, ctx, actor, true_out_response, logger=logger)
    # context without serialization
    if not isinstance(ctx, Context):
        raise Exception(f"ctx={ctx} has to have Context type")
    in_request, true_out_response = next(iterator)
    _, ctx = run_actor(in_request, ctx, actor, true_out_response, logger=logger)


if __name__ == "__main__":
    if is_in_notebook():
        run_auto_mode()
    else:
        run_interactive_mode(actor, logger)
