# %% [markdown]
"""
# Responses: 4. Multi Message

This tutorial shows how to store several messages inside a single one.
This might be useful if you want DFF Pipeline to send `response` candidates
to the messenger interface instead of a final response.

However, this approach is not recommended due to history incompleteness.
"""

# %pip install dff

# %%

from dff.script import TRANSITIONS, RESPONSE, Message
import dff.script.conditions as cnd

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)

# %%
toy_script = {
    "greeting_flow": {
        "start_node": {  # This is an initial node,
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
            # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: Message(
                misc={
                    "messages": [
                        Message("Hi, what is up?", misc={"confidences": 0.85}),
                        Message(
                            text="Hello, how are you?",
                            misc={"confidences": 0.9},
                        ),
                    ]
                }
            ),
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
            RESPONSE: Message("Sorry, I can not talk about that now."),
            TRANSITIONS: {"node4": cnd.exact_match(Message("Ok, goodbye."))},
        },
        "node4": {
            RESPONSE: Message("bye"),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
        },
        "fallback_node": {  # We get to this node
            # if an error occurred while the agent was running.
            RESPONSE: Message("Ooops"),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
        },
    }
}

# testing
happy_path = (
    (
        Message("Hi"),
        Message(
            misc={
                "messages": [
                    Message("Hi, what is up?", misc={"confidences": 0.85}),
                    Message(
                        text="Hello, how are you?", misc={"confidences": 0.9}
                    ),
                ]
            }
        ),
    ),  # start_node -> node1
    (
        Message("I'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about that now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("bye")),  # node3 -> node4
    (
        Message("Hi"),
        Message(
            misc={
                "messages": [
                    Message("Hi, what is up?", misc={"confidences": 0.85}),
                    Message(
                        text="Hello, how are you?", misc={"confidences": 0.9}
                    ),
                ]
            }
        ),
    ),  # node4 -> node1
    (
        Message("stop"),
        Message("Ooops"),
    ),
    # node1 -> fallback_node
    (
        Message("one"),
        Message("Ooops"),
    ),  # f_n->f_n
    (
        Message("help"),
        Message("Ooops"),
    ),  # f_n->f_n
    (
        Message("nope"),
        Message("Ooops"),
    ),  # f_n->f_n
    (
        Message("Hi"),
        Message(
            misc={
                "messages": [
                    Message("Hi, what is up?", misc={"confidences": 0.85}),
                    Message(
                        text="Hello, how are you?", misc={"confidences": 0.9}
                    ),
                ]
            }
        ),
    ),  # fallback_node -> node1
    (
        Message("I'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about that now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("bye")),  # node3 -> node4
)

# %%

pipeline = Pipeline.from_script(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
