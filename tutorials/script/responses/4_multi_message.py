# %% [markdown]
"""
# Responses: 4. Multi Message

This tutorial shows Multi Message usage.

The %mddoclink(api,script.core.message,MultiMessage) represents a combination of several messages.

Let's do all the necessary imports from DFF.
"""

# %pip install dff

# %%

from dff.script import TRANSITIONS, RESPONSE, Message, MultiMessage
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
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Hi"))},
            # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: MultiMessage(
                messages=[
                    Message(text="Hi, what is up?", misc={"confidences": 0.85}),
                    Message(text="Hello, how are you?", misc={"confidences": 0.9}),
                ]
            ),
            TRANSITIONS: {"node2": cnd.exact_match(Message(text="I'm fine, how are you?"))},
        },
        "node2": {
            RESPONSE: Message(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": cnd.exact_match(Message(text="Let's talk about music."))},
        },
        "node3": {
            RESPONSE: Message(text="Sorry, I can not talk about that now."),
            TRANSITIONS: {"node4": cnd.exact_match(Message(text="Ok, goodbye."))},
        },
        "node4": {
            RESPONSE: Message(text="bye"),
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Hi"))},
        },
        "fallback_node": {  # We get to this node
            # if an error occurred while the agent was running.
            RESPONSE: Message(text="Ooops"),
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Hi"))},
        },
    }
}

# testing
happy_path = (
    (
        Message(text="Hi"),
        MultiMessage(
            messages=[
                Message(text="Hi, what is up?", misc={"confidences": 0.85}),
                Message(text="Hello, how are you?", misc={"confidences": 0.9}),
            ]
        ),
    ),  # start_node -> node1
    (
        Message(text="I'm fine, how are you?"),
        Message(text="Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message(text="Let's talk about music."),
        Message(text="Sorry, I can not talk about that now."),
    ),  # node2 -> node3
    (Message(text="Ok, goodbye."), Message(text="bye")),  # node3 -> node4
    (
        Message(text="Hi"),
        MultiMessage(
            messages=[
                Message(text="Hi, what is up?", misc={"confidences": 0.85}),
                Message(text="Hello, how are you?", misc={"confidences": 0.9}),
            ]
        ),
    ),  # node4 -> node1
    (
        Message(text="stop"),
        Message(text="Ooops"),
    ),
    # node1 -> fallback_node
    (
        Message(text="one"),
        Message(text="Ooops"),
    ),  # f_n->f_n
    (
        Message(text="help"),
        Message(text="Ooops"),
    ),  # f_n->f_n
    (
        Message(text="nope"),
        Message(text="Ooops"),
    ),  # f_n->f_n
    (
        Message(text="Hi"),
        MultiMessage(
            messages=[
                Message(text="Hi, what is up?", misc={"confidences": 0.85}),
                Message(text="Hello, how are you?", misc={"confidences": 0.9}),
            ]
        ),
    ),  # fallback_node -> node1
    (
        Message(text="I'm fine, how are you?"),
        Message(text="Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message(text="Let's talk about music."),
        Message(text="Sorry, I can not talk about that now."),
    ),  # node2 -> node3
    (Message(text="Ok, goodbye."), Message(text="bye")),  # node3 -> node4
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
