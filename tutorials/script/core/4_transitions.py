# %% [markdown]
"""
# Core: 4. Transitions

This tutorial shows settings for transitions between flows and nodes.

Here, [conditions](%doclink(api,script.conditions.std_conditions))
for transition between many different script steps are shown.

Some of the destination steps can be set using
[labels](%doclink(api,script.labels.std_labels)).

First of all, let's do all the necessary imports from Chatsky.
"""


# %pip install chatsky

# %%
import re

from chatsky.script import TRANSITIONS, RESPONSE, Context, ConstLabel, Message
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
Let's define the functions with a special type of return value:

    ConstLabel == Flow Name; Node Name; Priority

These functions return Labels that
determine destination and priority of a specific transition.

Labels consist of:

1. Flow name of the destination node
   (optional; defaults to flow name of the current node).
2. Node name of the destination node
   (required).
3. Priority of the transition (more on that later)
   (optional; defaults to pipeline's
   [label_priority](%doclink(api,pipeline.pipeline.pipeline))).

An example of omitting optional arguments is shown in the body of the
`greeting_flow_n2_transition` function:
"""


# %%
def greeting_flow_n2_transition(_: Context, __: Pipeline) -> ConstLabel:
    return "greeting_flow", "node2"


def high_priority_node_transition(flow_name, node_name):
    def transition(_: Context, __: Pipeline) -> ConstLabel:
        return flow_name, node_name, 2.0

    return transition


# %% [markdown]
"""
Priority is needed to select a condition
in the situation where more than one condition is `True`.
All conditions in `TRANSITIONS` are being checked.
Of the set of `True` conditions,
the one that has the highest priority will be executed.
Of the set of `True` conditions with largest
priority the first met condition will be executed.

Out of the box `chatsky.script.core.labels`
offers the following methods:

* `lbl.repeat()` returns transition handler
    which returns `ConstLabel` to the last node,

* `lbl.previous()` returns transition handler
    which returns `ConstLabel` to the previous node,

* `lbl.to_start()` returns transition handler
    which returns `ConstLabel` to the start node,

* `lbl.to_fallback()` returns transition
    handler which returns `ConstLabel` to the fallback node,

* `lbl.forward()` returns transition handler
    which returns `ConstLabel` to the forward node,

* `lbl.backward()` returns transition handler
    which returns `ConstLabel` to the backward node.

There are three flows here: `global_flow`, `greeting_flow`, `music_flow`.
"""

# %%
toy_script = {
    "global_flow": {
        "start_node": {  # This is an initial node,
            # it doesn't need a `RESPONSE`.
            RESPONSE: Message(),
            TRANSITIONS: {
                ("music_flow", "node1"): cnd.regexp(
                    r"talk about music"
                ),  # first check
                ("greeting_flow", "node1"): cnd.regexp(
                    r"hi|hello", re.IGNORECASE
                ),  # second check
                "fallback_node": cnd.true(),  # third check
                # "fallback_node" is equivalent to
                # ("global_flow", "fallback_node").
            },
        },
        "fallback_node": {  # We get to this node if
            # an error occurred while the agent was running.
            RESPONSE: Message("Ooops"),
            TRANSITIONS: {
                ("music_flow", "node1"): cnd.regexp(
                    r"talk about music"
                ),  # first check
                ("greeting_flow", "node1"): cnd.regexp(
                    r"hi|hello", re.IGNORECASE
                ),  # second check
                lbl.previous(): cnd.regexp(
                    r"previous", re.IGNORECASE
                ),  # third check
                # lbl.previous() is equivalent
                # to ("previous_flow", "previous_node")
                lbl.repeat(): cnd.true(),  # fourth check
                # lbl.repeat() is equivalent to ("global_flow", "fallback_node")
            },
        },
    },
    "greeting_flow": {
        "node1": {
            RESPONSE: Message("Hi, how are you?"),
            # When the agent goes to node1, we return "Hi, how are you?"
            TRANSITIONS: {
                (
                    "global_flow",
                    "fallback_node",
                    0.1,
                ): cnd.true(),  # second check
                "node2": cnd.regexp(r"how are you"),  # first check
                # "node2" is equivalent to ("greeting_flow", "node2", 1.0)
            },
        },
        "node2": {
            RESPONSE: Message("Good. What do you want to talk about?"),
            TRANSITIONS: {
                lbl.to_fallback(0.1): cnd.true(),  # fourth check
                # lbl.to_fallback(0.1) is equivalent
                # to ("global_flow", "fallback_node", 0.1)
                lbl.forward(0.5): cnd.regexp(r"talk about"),  # third check
                # lbl.forward(0.5) is equivalent
                # to ("greeting_flow", "node3", 0.5)
                ("music_flow", "node1"): cnd.regexp(
                    r"talk about music"
                ),  # first check
                # ("music_flow", "node1") is equivalent
                # to ("music_flow", "node1", 1.0)
                lbl.previous(): cnd.regexp(
                    r"previous", re.IGNORECASE
                ),  # second check
            },
        },
        "node3": {
            RESPONSE: Message("Sorry, I can not talk about that now."),
            TRANSITIONS: {lbl.forward(): cnd.regexp(r"bye")},
        },
        "node4": {
            RESPONSE: Message("Bye"),
            TRANSITIONS: {
                "node1": cnd.regexp(r"hi|hello", re.IGNORECASE),  # first check
                lbl.to_fallback(): cnd.true(),  # second check
            },
        },
    },
    "music_flow": {
        "node1": {
            RESPONSE: Message(
                text="I love `System of a Down` group, "
                "would you like to talk about it?"
            ),
            TRANSITIONS: {
                lbl.forward(): cnd.regexp(r"yes|yep|ok", re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        "node2": {
            RESPONSE: Message(
                text="System of a Down is "
                "an Armenian-American heavy metal band formed in 1994."
            ),
            TRANSITIONS: {
                lbl.forward(): cnd.regexp(r"next", re.IGNORECASE),
                lbl.repeat(): cnd.regexp(r"repeat", re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        "node3": {
            RESPONSE: Message(
                text="The band achieved commercial success "
                "with the release of five studio albums."
            ),
            TRANSITIONS: {
                lbl.forward(): cnd.regexp(r"next", re.IGNORECASE),
                lbl.backward(): cnd.regexp(r"back", re.IGNORECASE),
                lbl.repeat(): cnd.regexp(r"repeat", re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        "node4": {
            RESPONSE: Message("That's all what I know."),
            TRANSITIONS: {
                greeting_flow_n2_transition: cnd.regexp(
                    r"next", re.IGNORECASE
                ),  # second check
                high_priority_node_transition(
                    "greeting_flow", "node4"
                ): cnd.regexp(
                    r"next time", re.IGNORECASE
                ),  # first check
                lbl.to_fallback(): cnd.true(),  # third check
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
    ("next time", "Bye"),
    ("stop", "Ooops"),
    ("previous", "Bye"),
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
    ("Ok, goodbye.", "Bye"),
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
