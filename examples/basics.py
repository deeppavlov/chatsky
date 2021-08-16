import logging
import re
from typing import Optional

from dff.core.keywords import TRANSITIONS, GRAPH, RESPONSE
from dff.core import Context, Actor

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


any_text_pattern = re.compile(r".*")

flows = {
    "greeting_flow": {
        GRAPH: {
            "node0": {
                RESPONSE: "",
                TRANSITIONS: {
                    "node1": "Hi",
                    "node0": any_text_pattern,
                },
            },
            "node1": {
                RESPONSE: "Hi, how are you?",
                TRANSITIONS: {
                    "node2": "i'm fine, how are you?",
                    "node1": any_text_pattern,
                },
            },
            "node2": {
                RESPONSE: "Good. What do you want to talk about?",
                TRANSITIONS: {
                    "node3": "Let's talk about music.",
                    "node2": any_text_pattern,
                },
            },
            "node3": {
                RESPONSE: "Sorry, I can not talk about music now.",
                TRANSITIONS: {
                    "node4": "Ok, goodbye.",
                    "node3": any_text_pattern,
                },
            },
            "node4": {
                RESPONSE: "bye",
                TRANSITIONS: {
                    "node1": "Hi",
                    "node4": any_text_pattern,
                },
            },
        }
    },
}

actor = Actor(flows, start_node_label=("greeting_flow", "node0"))


def turn_handler(in_request: str, ctx: Context, actor: Actor, true_out_response: Optional[str] = None):
    ctx = Context.cast(ctx)
    ctx.add_human_utterance(in_request)
    ctx = actor(ctx)
    out_response = ctx.actor_text_response
    if true_out_response is not None and true_out_response != out_response:
        raise Exception(f"{in_request=} -> true_out_response != out_response: {true_out_response} != {out_response}")
    else:
        logging.info(f"{in_request=} -> {out_response}")
    return out_response, ctx


# testing
in_requests = [
    "Hi",
    "i'm fine, how are you?",
    "Let's talk about music.",
    "Ok, goodbye.",
    "Hi",
]
out_responses = [
    "Hi, how are you?",
    "Good. What do you want to talk about?",
    "Sorry, I can not talk about music now.",
    "bye",
    "Hi, how are you?",
]


def run_test():
    ctx = {}
    for in_request, true_out_response in zip(in_requests, out_responses):
        _, ctx = turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


# interactive mode
def run_interactive_mode(actor):
    ctx = {}
    while True:
        in_request = input("type your answer: ")
        _, ctx = turn_handler(in_request, ctx, actor)


if __name__ == "__main__":
    run_test()
    run_interactive_mode(actor)
