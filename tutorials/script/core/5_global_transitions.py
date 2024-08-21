# %% [markdown]
"""
# Core: 5. Global transitions

This tutorial shows the global setting of transitions.

Here, global [conditions](%doclink(api,script.conditions.std_conditions))
for default transition between many different script steps are shown.

First of all, let's do all the necessary imports from Chatsky.
"""


# %pip install chatsky

# %%
import re

from chatsky.script import GLOBAL, TRANSITIONS, RESPONSE, Message
import chatsky.script.conditions as cnd
import chatsky.script.labels as lbl
from chatsky.pipeline import Pipeline
from chatsky.utils.testing.common import (
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
    ("hi", "Hi, how are you?"),
    (
        "i'm fine, how are you?",
        "Good. What do you want to talk about?",
    ),
    (
        "talk about music.",
        "I love `System of a Down` group, " "would you like to talk about it?",
    ),
    (
        "yes",
        "System of a Down is "
        "an Armenian-American heavy metal band formed in 1994.",
    ),
    (
        "next",
        "The band achieved commercial success "
        "with the release of five studio albums.",
    ),
    (
        "back",
        "System of a Down is "
        "an Armenian-American heavy metal band formed in 1994.",
    ),
    (
        "repeat",
        "System of a Down is "
        "an Armenian-American heavy metal band formed in 1994.",
    ),
    (
        "next",
        "The band achieved commercial success "
        "with the release of five studio albums.",
    ),
    ("next", "That's all what I know."),
    (
        "next",
        "Good. What do you want to talk about?",
    ),
    ("previous", "That's all what I know."),
    ("next time", "bye"),
    ("stop", "Ooops"),
    ("previous", "bye"),
    ("stop", "Ooops"),
    ("nope", "Ooops"),
    ("hi", "Hi, how are you?"),
    ("stop", "Ooops"),
    ("previous", "Hi, how are you?"),
    (
        "i'm fine, how are you?",
        "Good. What do you want to talk about?",
    ),
    (
        "let's talk about something.",
        "Sorry, I can not talk about that now.",
    ),
    ("Ok, goodbye.", "bye"),
)

# %%
pipeline = Pipeline(
    script=toy_script,
    start_label=("global_flow", "start_node"),
    fallback_label=("global_flow", "fallback_node"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
