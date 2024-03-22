# %% [markdown]
"""
# Core: 5. Global transitions

This tutorial shows the global setting of transitions.

Here, global [conditions](%doclink(api,script.conditions.std_conditions))
for default transition between many different script steps are shown.

First of all, let's do all the necessary imports from DFF.
"""


# %pip install dff

# %%
import re

from dff.script import GLOBAL, TRANSITIONS, RESPONSE, Message
import dff.script.conditions as cnd
import dff.script.labels as lbl
from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)

# %% [markdown]
"""
The keyword `GLOBAL` is used to define a global node.
There can be only one global node in a script.
The value that corresponds to this key has the
`dict` type with the same keywords as regular nodes.
The global node is defined above the flow level as opposed to regular nodes.
This node allows to define default global values for all nodes.

There are `GLOBAL` node and three flows:
`global_flow`, `greeting_flow`, `music_flow`.
"""

# %%
toy_script = {
    GLOBAL: {
        TRANSITIONS: {
            ("greeting_flow", "node1", 1.1): cnd.regexp(
                r"\b(hi|hello)\b", re.I
            ),  # first check
            ("music_flow", "node1", 1.1): cnd.regexp(
                r"talk about music"
            ),  # second check
            lbl.to_fallback(0.1): cnd.true(),  # fifth check
            lbl.forward(): cnd.all(
                [
                    cnd.regexp(r"next\b"),
                    cnd.has_last_labels(
                        labels=[("music_flow", i) for i in ["node2", "node3"]]
                    ),
                ]  # third check
            ),
            lbl.repeat(0.2): cnd.all(
                [
                    cnd.regexp(r"repeat", re.I),
                    cnd.negation(
                        cnd.has_last_labels(flow_labels=["global_flow"])
                    ),
                ]  # fourth check
            ),
        }
    },
    "global_flow": {
        "start_node": {
            RESPONSE: Message()
        },  # This is an initial node, it doesn't need a `RESPONSE`.
        "fallback_node": {  # We get to this node
            # if an error occurred while the agent was running.
            RESPONSE: Message("Ooops"),
            TRANSITIONS: {lbl.previous(): cnd.regexp(r"previous", re.I)},
            # lbl.previous() is equivalent to
            # ("previous_flow", "previous_node", 1.0)
        },
    },
    "greeting_flow": {
        "node1": {
            RESPONSE: Message("Hi, how are you?"),
            TRANSITIONS: {"node2": cnd.regexp(r"how are you")},
            # "node2" is equivalent to ("greeting_flow", "node2", 1.0)
        },
        "node2": {
            RESPONSE: Message("Good. What do you want to talk about?"),
            TRANSITIONS: {
                lbl.forward(0.5): cnd.regexp(r"talk about"),
                # lbl.forward(0.5) is equivalent to
                # ("greeting_flow", "node3", 0.5)
                lbl.previous(): cnd.regexp(r"previous", re.I),
            },
        },
        "node3": {
            RESPONSE: Message("Sorry, I can not talk about that now."),
            TRANSITIONS: {lbl.forward(): cnd.regexp(r"bye")},
        },
        "node4": {RESPONSE: Message("bye")},
        # Only the global transitions setting are used in this node.
    },
    "music_flow": {
        "node1": {
            RESPONSE: Message(
                text="I love `System of a Down` group, "
                "would you like to talk about it?"
            ),
            TRANSITIONS: {lbl.forward(): cnd.regexp(r"yes|yep|ok", re.I)},
        },
        "node2": {
            RESPONSE: Message(
                text="System of a Down is "
                "an Armenian-American heavy metal band formed in 1994."
            )
            # Only the global transitions setting are used in this node.
        },
        "node3": {
            RESPONSE: Message(
                text="The band achieved commercial success "
                "with the release of five studio albums."
            ),
            TRANSITIONS: {lbl.backward(): cnd.regexp(r"back", re.I)},
        },
        "node4": {
            RESPONSE: Message("That's all what I know."),
            TRANSITIONS: {
                ("greeting_flow", "node4"): cnd.regexp(r"next time", re.I),
                ("greeting_flow", "node2"): cnd.regexp(r"next", re.I),
            },
        },
    },
}

# testing
happy_path = (
    (Message("hi"), Message("Hi, how are you?")),
    (
        Message("i'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),
    (
        Message("talk about music."),
        Message(
            text="I love `System of a Down` group, "
            "would you like to talk about it?"
        ),
    ),
    (
        Message("yes"),
        Message(
            text="System of a Down is "
            "an Armenian-American heavy metal band formed in 1994."
        ),
    ),
    (
        Message("next"),
        Message(
            text="The band achieved commercial success "
            "with the release of five studio albums."
        ),
    ),
    (
        Message("back"),
        Message(
            text="System of a Down is "
            "an Armenian-American heavy metal band formed in 1994."
        ),
    ),
    (
        Message("repeat"),
        Message(
            text="System of a Down is "
            "an Armenian-American heavy metal band formed in 1994."
        ),
    ),
    (
        Message("next"),
        Message(
            text="The band achieved commercial success "
            "with the release of five studio albums."
        ),
    ),
    (Message("next"), Message("That's all what I know.")),
    (
        Message("next"),
        Message("Good. What do you want to talk about?"),
    ),
    (Message("previous"), Message("That's all what I know.")),
    (Message("next time"), Message("bye")),
    (Message("stop"), Message("Ooops")),
    (Message("previous"), Message("bye")),
    (Message("stop"), Message("Ooops")),
    (Message("nope"), Message("Ooops")),
    (Message("hi"), Message("Hi, how are you?")),
    (Message("stop"), Message("Ooops")),
    (Message("previous"), Message("Hi, how are you?")),
    (
        Message("i'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),
    (
        Message("let's talk about something."),
        Message("Sorry, I can not talk about that now."),
    ),
    (Message("Ok, goodbye."), Message("bye")),
)

# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("global_flow", "start_node"),
    fallback_label=("global_flow", "fallback_node"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
