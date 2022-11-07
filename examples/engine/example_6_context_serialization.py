"""
6. Context serialization
========================
"""

import logging

from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE
from dff.core.engine.core import Context, Actor
import dff.core.engine.conditions as cnd
from dff.utils.common import run_example

logger = logging.getLogger(__name__)


def response_handler(ctx: Context, actor: Actor, *args, **kwargs) -> str:
    return f"answer {len(ctx.requests)}"


# a dialog script
script = {
    "flow_start": {"node_start": {RESPONSE: response_handler, TRANSITIONS: {("flow_start", "node_start"): cnd.true()}}}
}


actor = Actor(script, start_label=("flow_start", "node_start"))


testing_dialog = [("hi", "answer 1"), ("how are you?", "answer 2"), ("ok", "answer 3"), ("good", "answer 4")]


def process_response(ctx: Context):
    ctx_json = ctx.json()
    if isinstance(ctx_json, str):
        logging.info("context serialized to json str")
    else:
        raise Exception(f"ctx={ctx_json} has to be serialized to json string")

    ctx_dict = ctx.dict()
    if isinstance(ctx_dict, dict):
        logging.info("context serialized to dict")
    else:
        raise Exception(f"ctx={ctx_dict} has to be serialized to dict")

    if not isinstance(ctx, Context):
        raise Exception(f"ctx={ctx} has to have Context type")


if __name__ == "__main__":
    run_example(logger, actor=actor, response_wrapper=process_response)
