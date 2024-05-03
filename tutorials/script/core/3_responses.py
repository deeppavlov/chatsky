# %% [markdown]
"""
# Core: 3. Responses

This tutorial shows different options for setting responses.

Here, [responses](%doclink(api,script.responses.std_responses))
that allow giving custom answers to users are shown.

Let's do all the necessary imports from DFF.
"""

# %pip install dff

# %%
import re
import random

from dff.script import TRANSITIONS, RESPONSE, Context, Message
import dff.script.responses as rsp
import dff.script.conditions as cnd

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)


# %% [markdown]
"""
The response can be set by Callable or *Message:

* Callable objects. If the object is callable it must have a special signature:

        func(ctx: Context, pipeline: Pipeline) -> Message

* *Message objects. If the object is *Message
    it will be returned by the agent as a response.


The functions to be used in the `toy_script` are declared here.
"""


# %%
def cannot_talk_about_topic_response(ctx: Context, _: Pipeline) -> Message:
    request = ctx.last_request
    if request is None or request.text is None:
        topic = None
    else:
        topic_pattern = re.compile(r"(.*talk about )(.*)\.")
        topic = topic_pattern.findall(request.text)
        topic = topic and topic[0] and topic[0][-1]
    if topic:
        return Message(f"Sorry, I can not talk about {topic} now.")
    else:
        return Message("Sorry, I can not talk about that now.")


def upper_case_response(response: Message):
    # wrapper for internal response function
    def func(_: Context, __: Pipeline) -> Message:
        if response.text is not None:
            response.text = response.text.upper()
        return response

    return func


def fallback_trace_response(ctx: Context, _: Pipeline) -> Message:
    return Message(
        misc={
            "previous_node": list(ctx.labels.values())[-2],
            "last_request": ctx.last_request,
        }
    )


# %%
toy_script = {
    "greeting_flow": {
        "start_node": {  # This is an initial node,
            # it doesn't need a `RESPONSE`.
            RESPONSE: Message(),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
            # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: rsp.choice(
                [
                    Message("Hi, what is up?"),
                    Message("Hello, how are you?"),
                ]
            ),
            # Random choice from candidate list.
            TRANSITIONS: {
                "node2": cnd.exact_match(Message("I'm fine, how are you?"))
            },
        },
        "node2": {
            RESPONSE: Message("Good. What do you want to talk about?"),
            TRANSITIONS: {
                "node3": cnd.exact_match(Message("Let's talk about music."))
            },
        },
        "node3": {
            RESPONSE: cannot_talk_about_topic_response,
            TRANSITIONS: {"node4": cnd.exact_match(Message("Ok, goodbye."))},
        },
        "node4": {
            RESPONSE: upper_case_response(Message("bye")),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
        },
        "fallback_node": {  # We get to this node
            # if an error occurred while the agent was running.
            RESPONSE: fallback_trace_response,
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
        },
    }
}

# testing
happy_path = (
    (
        Message("Hi"),
        Message("Hello, how are you?"),
    ),  # start_node -> node1
    (
        Message("I'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("BYE")),  # node3 -> node4
    (Message("Hi"), Message("Hello, how are you?")),  # node4 -> node1
    (
        Message("stop"),
        Message(
            misc={
                "previous_node": ("greeting_flow", "node1"),
                "last_request": Message("stop"),
            }
        ),
    ),
    # node1 -> fallback_node
    (
        Message("one"),
        Message(
            misc={
                "previous_node": ("greeting_flow", "fallback_node"),
                "last_request": Message("one"),
            }
        ),
    ),  # f_n->f_n
    (
        Message("help"),
        Message(
            misc={
                "previous_node": ("greeting_flow", "fallback_node"),
                "last_request": Message("help"),
            }
        ),
    ),  # f_n->f_n
    (
        Message("nope"),
        Message(
            misc={
                "previous_node": ("greeting_flow", "fallback_node"),
                "last_request": Message("nope"),
            }
        ),
    ),  # f_n->f_n
    (
        Message("Hi"),
        Message("Hi, what is up?"),
    ),  # fallback_node -> node1
    (
        Message("I'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("BYE")),  # node3 -> node4
)

# %%
random.seed(31415)  # predestination of choice


pipeline = Pipeline.from_script(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
