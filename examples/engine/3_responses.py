# %% [markdown]
"""
3. Responses
============

This example shows different options for setting responses. Let's do all the necessary imports from `dff`.
"""


# %%
# pip install dff  # Uncomment this line to install the framework


# %%
import re
import random
from typing import Any

from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE
from dff.core.engine.core import Actor, Context
import dff.core.engine.responses as rsp
import dff.core.engine.conditions as cnd

from dff.core.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, is_interactive_mode, run_interactive_mode


# %% [markdown]
"""
The response can be set by any object of python:

* Callable objects. If the object is callable it must have a special signature:

        func(ctx: Context, actor: Actor, *args, **kwargs) -> Any

* Non-callable objects. If the object is not callable, it will be returned by the agent as a response.

Out of the box `DSL` has a single response function `choice` that gives one random response from the list of responses.

The functions to be used in the `toy_script` are declared here.
"""


# %%
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
    return {"previous_node": list(ctx.labels.values())[-2], "last_request": ctx.last_request}


# %%
toy_script = {
    "greeting_flow": {
        "start_node": {  # This is an initial node, it doesn't need a `RESPONSE`.
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
            # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: rsp.choice(["Hi, what is up?", "Hello, how are you?"]),
            # Random choice from candicate list.
            TRANSITIONS: {"node2": cnd.exact_match("I'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": cnd.exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: cannot_talk_about_topic_response,
            TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")},
        },
        "node4": {
            RESPONSE: upper_case_response("bye"),
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
        "fallback_node": {  # We get to this node if an error occurred while the agent was running.
            RESPONSE: fallback_trace_response,
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
    }
}

# testing
happy_path = (
    ("Hi", "Hello, how are you?"),  # start_node -> node1
    ("I'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "BYE"),  # node3 -> node4
    ("Hi", "Hi, what is up?"),  # node4 -> node1
    ("stop", {"previous_node": ("greeting_flow", "node1"), "last_request": "stop"}),
    # node1 -> fallback_node
    ("one", {"previous_node": ("greeting_flow", "fallback_node"), "last_request": "one"}),  # f_n->f_n
    ("help", {"previous_node": ("greeting_flow", "fallback_node"), "last_request": "help"}),  # f_n->f_n
    ("nope", {"previous_node": ("greeting_flow", "fallback_node"), "last_request": "nope"}),  # f_n->f_n
    ("Hi", "Hello, how are you?"),  # fallback_node -> node1
    ("I'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "BYE"),  # node3 -> node4
)

# %%
random.seed(31415)  # predestination of choice


pipeline = Pipeline.from_script(
    toy_script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node")
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
