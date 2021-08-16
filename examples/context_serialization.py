import logging
import json

from dff.core.keywords import TRANSITIONS, GRAPH, RESPONSE
from dff.core import Context, Actor

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# custom functions
def always_true(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


def response_handler(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return f"answer {len(ctx.human_utterances)}"


# a dialog script
flows = {
    "flow_start": {
        GRAPH: {
            "node_start": {
                RESPONSE: response_handler,
                TRANSITIONS: {
                    ("flow_start", "node_start"): always_true,
                },
            }
        },
    },
}

actor = Actor(flows, start_node_label=("flow_start", "node_start"))


def turn_handler(in_request, ctx={}, true_out_response=None):
    ctx = Context.cast(ctx)
    ctx.add_human_utterance(in_request)
    ctx = actor(ctx)
    out_response = ctx.actor_text_response
    # Below
    if true_out_response is not None and true_out_response != out_response:
        logging.error(f"{in_request=} -> true_out_response != out_response: {true_out_response} != {out_response}")
    else:
        logging.info(f"{in_request=} -> {out_response}")
    return out_response, ctx


in_requests = ["hi", "how are you?", "ok", "good"]
out_responses = ["answer 1", "answer 2", "answer 3", "answer 4"]


def run_test():
    ctx = {}
    iterator = zip(in_requests, out_responses)
    in_request, true_out_response = next(iterator)
    # pass as empty context
    _, ctx = turn_handler(in_request, ctx=ctx, true_out_response=true_out_response)
    # serialize context to json str
    ctx = ctx.json()
    if isinstance(ctx, str):
        logging.info("context serialized to json str")
    else:
        logging.error(f"{ctx=} has to be serialized to json string")
    in_request, true_out_response = next(iterator)
    _, ctx = turn_handler(in_request, ctx=ctx, true_out_response=true_out_response)
    # serialize context to dict
    ctx = ctx.dict()
    if isinstance(ctx, dict):
        logging.info("context serialized to dict")
    else:
        logging.error(f"{ctx=} has to be serialized to dict")
    in_request, true_out_response = next(iterator)
    _, ctx = turn_handler(in_request, ctx=ctx, true_out_response=true_out_response)
    # context without serialization
    if not isinstance(ctx, Context):
        logging.error(f"{ctx=} has to have Context type")
    in_request, true_out_response = next(iterator)
    _, ctx = turn_handler(in_request, ctx=ctx, true_out_response=true_out_response)


def run_interactive_mode():
    ctx = {}
    while True:
        in_request = input("type your answer: ")
        _, ctx = turn_handler(in_request, ctx=ctx)


if __name__ == "__main__":
    run_test()
    run_interactive_mode()
