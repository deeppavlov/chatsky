import logging
import re
import random
from typing import Any

from df_engine.core.keywords import TRANSITIONS, RESPONSE
from df_engine.core import Actor, Context
import df_engine.responses as rsp
import df_engine.conditions as cnd

from examples import example_1_basics

logger = logging.getLogger(__name__)


# Here we will consider different options for setting responses.

# The response is set by any object of python:
#
# - collable objects - If the object is callable, then it must have a special signature:
#                      func`(ctx: Context, actor: Actor, *args, **kwargs) -> Any`
#                      Then this object will be called with the appropriate arguments.
#
# - non-callable objects - If the object is not callable,
#                          then the object will be returned by the agent as a response.


# Out of the box, df_engine offers 1 additional response function:
# - `choice` - will return `true` if the user's request completely matches the value passed to the function.


def cannot_talk_about_topic_response(ctx: Context, actor: Actor, *args, **kwargs) -> Any:
    request = ctx.last_request
    topic_pattern = re.compile(r"(.*talk about )(.*)\.")
    topic = topic_pattern.findall(request)
    topic = topic and topic[0] and topic[0][-1]
    if topic:
        return f"Sorry, I can not talk about {topic} now."
    else:
        return "Sorry, I can not talk about that now."


def upper_case_response(response: str):
    # wrapper for internal response function
    def cannot_talk_about_topic_response(ctx: Context, actor: Actor, *args, **kwargs) -> Any:
        return response.upper()

    return cannot_talk_about_topic_response


def fallback_trace_response(ctx: Context, actor: Actor, *args, **kwargs) -> Any:
    logger.warning(f"ctx={ctx}")
    return {"previous_node": list(ctx.labels.values())[-2], "last_request": ctx.last_request}


plot = {
    "greeting_flow": {
        "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},  # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: rsp.choice(["Hi, what is up?", "Hello, how are you?"]),  # random choice from candicate list
            TRANSITIONS: {"node2": cnd.exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": cnd.exact_match("Let's talk about music.")},
        },
        "node3": {RESPONSE: cannot_talk_about_topic_response, TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")}},
        "node4": {RESPONSE: upper_case_response("bye"), TRANSITIONS: {"node1": cnd.exact_match("Hi")}},
        "fallback_node": {  # We get to this node if an error occurred while the agent was running
            RESPONSE: fallback_trace_response,
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
    }
}


actor = Actor(plot, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))


# testing
testing_dialog = [
    ("Hi", "Hello, how are you?"),  # start_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "BYE"),  # node3 -> node4
    ("Hi", "Hello, how are you?"),  # node4 -> node1
    ("stop", {"previous_node": ("greeting_flow", "node1"), "last_request": "stop"}),  # node1 -> fallback_node
    ("one", {"previous_node": ("greeting_flow", "fallback_node"), "last_request": "one"}),  # f_n->f_n
    ("help", {"previous_node": ("greeting_flow", "fallback_node"), "last_request": "help"}),  # f_n->f_n
    ("nope", {"previous_node": ("greeting_flow", "fallback_node"), "last_request": "nope"}),  # f_n->f_n
    ("Hi", "Hi, what is up?"),  # fallback_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "BYE"),  # node3 -> node4
]


random.seed(31415)  # predestination of choice


def run_test():
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s", level=logging.INFO
    )
    # run_test()
    example_1_basics.run_interactive_mode(actor)
