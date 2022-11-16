"""
4. Transitions
==============
"""

# TODO:
# 1. Maybe remove `lbl.to_fallback(): cnd.true(),` from script as a trivial condition?

import re

from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE
from dff.core.engine.core import Context, Actor
import dff.core.engine.conditions as cnd
import dff.core.engine.labels as lbl
from dff.core.engine.core.types import NodeLabel3Type
from dff.core.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, is_interactive_mode, run_interactive_mode


# def always_true_condition(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
#     return True

# `always_true_condition` is same cnd.true()


# NodeLabel3Type == tuple[str, str, float]
def greeting_flow_n2_transition(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
    return ("greeting_flow", "node2", 1.0)


def high_priority_node_transition(flow_label, label):
    def transition(ctx: Context, actor: Actor, *args, **kwargs) -> NodeLabel3Type:
        return (flow_label, label, 2.0)

    return transition


toy_script = {
    "global_flow": {
        "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {
                ("music_flow", "node1"): cnd.regexp(r"talk about music"),  # first check
                ("greeting_flow", "node1"): cnd.regexp(r"hi|hello", re.IGNORECASE),  # second check
                # ("global_flow", "fallback_node"): cnd.true(),  # third check
                "fallback_node": cnd.true(),  # third check
                # "fallback_node" is equivalent to ("global_flow", "fallback_node")
            },
        },
        "fallback_node": {  # We get to this node if an error occurred while the agent was running
            RESPONSE: "Ooops",
            TRANSITIONS: {
                ("music_flow", "node1"): cnd.regexp(r"talk about music"),  # first check
                ("greeting_flow", "node1"): cnd.regexp(r"hi|hello", re.IGNORECASE),  # second check
                lbl.previous(): cnd.regexp(r"previous", re.IGNORECASE),  # third check
                # lbl.previous() is equivalent to ("PREVIOUS_flow", "PREVIOUS_node")
                lbl.repeat(): cnd.true(),  # fourth check
                # lbl.repeat() is equivalent to ("global_flow", "fallback_node")
            },
        },
    },
    "greeting_flow": {
        "node1": {
            RESPONSE: "Hi, how are you?",  # When the agent goes to node1, we return "Hi, how are you?"
            TRANSITIONS: {
                ("global_flow", "fallback_node", 0.1): cnd.true(),  # second check
                "node2": cnd.regexp(r"how are you"),  # first check
                # "node2" is equivalent to ("greeting_flow", "node2", 1.0)
            },
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {
                lbl.to_fallback(0.1): cnd.true(),  # third check
                # lbl.to_fallback(0.1) is equivalent to ("global_flow", "fallback_node", 0.1)
                lbl.forward(0.5): cnd.regexp(r"talk about"),  # second check
                # lbl.forward(0.5) is equivalent to ("greeting_flow", "node3", 0.5)
                ("music_flow", "node1"): cnd.regexp(r"talk about music"),  # first check
                lbl.previous(): cnd.regexp(r"previous", re.IGNORECASE),  # third check
                # ("music_flow", "node1") is equivalent to ("music_flow", "node1", 1.0)
            },
        },
        "node3": {RESPONSE: "Sorry, I can not talk about that now.", TRANSITIONS: {lbl.forward(): cnd.regexp(r"bye")}},
        "node4": {
            RESPONSE: "bye",
            TRANSITIONS: {
                "node1": cnd.regexp(r"hi|hello", re.IGNORECASE),  # first check
                lbl.to_fallback(): cnd.true(),  # second check
            },
        },
    },
    "music_flow": {
        "node1": {
            RESPONSE: "I love `System of a Down` group, would you like to tell about it? ",
            TRANSITIONS: {lbl.forward(): cnd.regexp(r"yes|yep|ok", re.IGNORECASE), lbl.to_fallback(): cnd.true()},
        },
        "node2": {
            RESPONSE: "System of a Down is an Armenian-American heavy metal band formed in 1994.",
            TRANSITIONS: {
                lbl.forward(): cnd.regexp(r"next", re.IGNORECASE),
                lbl.repeat(): cnd.regexp(r"repeat", re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        "node3": {
            RESPONSE: "The band achieved commercial success with the release of five studio albums.",
            TRANSITIONS: {
                lbl.forward(): cnd.regexp(r"next", re.IGNORECASE),
                lbl.backward(): cnd.regexp(r"back", re.IGNORECASE),
                lbl.repeat(): cnd.regexp(r"repeat", re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),
            },
        },
        "node4": {
            RESPONSE: "That's all what I know",
            TRANSITIONS: {
                greeting_flow_n2_transition: cnd.regexp(r"next", re.IGNORECASE),  # second check
                high_priority_node_transition("greeting_flow", "node4"): cnd.regexp(r"next time", re.IGNORECASE),
                lbl.to_fallback(): cnd.true(),  # third check
            },
        },
    },
}


# testing
happy_path = (
    ("hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("talk about music.", "I love `System of a Down` group, would you like to tell about it? "),
    ("yes", "System of a Down is an Armenian-American heavy metal band formed in 1994."),
    ("next", "The band achieved commercial success with the release of five studio albums."),
    ("back", "System of a Down is an Armenian-American heavy metal band formed in 1994."),
    ("repeat", "System of a Down is an Armenian-American heavy metal band formed in 1994."),
    ("next", "The band achieved commercial success with the release of five studio albums."),
    ("next", "That's all what I know"),
    ("next", "Good. What do you want to talk about?"),
    ("previous", "That's all what I know"),
    ("next time", "bye"),
    ("stop", "Ooops"),
    ("previous", "bye"),
    ("stop", "Ooops"),
    ("nope", "Ooops"),
    ("hi", "Hi, how are you?"),
    ("stop", "Ooops"),
    ("previous", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("let's talk about something.", "Sorry, I can not talk about that now."),
    ("Ok, goodbye.", "bye"),
)


pipeline = Pipeline.from_script(
    toy_script, start_label=("global_flow", "start_node"), fallback_label=("global_flow", "fallback_node")
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
