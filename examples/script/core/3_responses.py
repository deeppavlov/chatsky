# %% [markdown]
"""
# 3. Responses

This example shows different options for setting responses.
Let's do all the necessary imports from `dff`.
"""


# %%
import re
import random

from dff.script import TRANSITIONS, RESPONSE, Actor, Context, Message
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

        func(ctx: Context, actor: Actor, *args, **kwargs) -> Any

* *Message objects. If the object is *Message
    it will be returned by the agent as a response.


The functions to be used in the `toy_script` are declared here.
"""


# %%
def cannot_talk_about_topic_response(ctx: Context, line: Pipeline, *args, **kwargs) -> Message:
    request = ctx.last_request
    if request is None or request.text is None:
        topic = None
    else:
        topic_pattern = re.compile(r"(.*talk about )(.*)\.")
        topic = topic_pattern.findall(request.text)
        topic = topic and topic[0] and topic[0][-1]
    if topic:
        return Message(text=f"Sorry, I can not talk about {topic} now.")
    else:
        return Message(text="Sorry, I can not talk about that now.")


def upper_case_response(response: Message):
    # wrapper for internal response function
    def func(ctx: Context, line: Pipeline, *args, **kwargs) -> Message:
        if response.text is not None:
            response.text = response.text.upper()
        return response

    return func


def fallback_trace_response(ctx: Context, line: Pipeline, *args, **kwargs) -> Message:
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
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Hi"))},
            # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: rsp.choice(
                [Message(text="Hi, what is up?"), Message(text="Hello, how are you?")]
            ),
            # Random choice from candicate list.
            TRANSITIONS: {"node2": cnd.exact_match(Message(text="I'm fine, how are you?"))},
        },
        "node2": {
            RESPONSE: Message(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": cnd.exact_match(Message(text="Let's talk about music."))},
        },
        "node3": {
            RESPONSE: cannot_talk_about_topic_response,
            TRANSITIONS: {"node4": cnd.exact_match(Message(text="Ok, goodbye."))},
        },
        "node4": {
            RESPONSE: upper_case_response(Message(text="bye")),
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Hi"))},
        },
        "fallback_node": {  # We get to this node
            # if an error occurred while the agent was running.
            RESPONSE: fallback_trace_response,
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Hi"))},
        },
    }
}

# testing
happy_path = (
    (Message(text="Hi"), Message(text="Hello, how are you?")),  # start_node -> node1
    (
        Message(text="I'm fine, how are you?"),
        Message(text="Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message(text="Let's talk about music."),
        Message(text="Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message(text="Ok, goodbye."), Message(text="BYE")),  # node3 -> node4
    (Message(text="Hi"), Message(text="Hi, what is up?")),  # node4 -> node1
    (
        Message(text="stop"),
        Message(
            misc={"previous_node": ("greeting_flow", "node1"), "last_request": Message(text="stop")}
        ),
    ),
    # node1 -> fallback_node
    (
        Message(text="one"),
        Message(
            misc={
                "previous_node": ("greeting_flow", "fallback_node"),
                "last_request": Message(text="one"),
            }
        ),
    ),  # f_n->f_n
    (
        Message(text="help"),
        Message(
            misc={
                "previous_node": ("greeting_flow", "fallback_node"),
                "last_request": Message(text="help"),
            }
        ),
    ),  # f_n->f_n
    (
        Message(text="nope"),
        Message(
            misc={
                "previous_node": ("greeting_flow", "fallback_node"),
                "last_request": Message(text="nope"),
            }
        ),
    ),  # f_n->f_n
    (Message(text="Hi"), Message(text="Hello, how are you?")),  # fallback_node -> node1
    (
        Message(text="I'm fine, how are you?"),
        Message(text="Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message(text="Let's talk about music."),
        Message(text="Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message(text="Ok, goodbye."), Message(text="BYE")),  # node3 -> node4
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
