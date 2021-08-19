import logging
from typing import Optional, Union
import re

from dff.core.keywords import TRANSITIONS, GRAPH, RESPONSE
from dff.core import Context, Actor
from dff.conditions import exact_match, regexp
from dff.transitions import to_fallback, forward

from examples import example_1_basics

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# First of all, to create a dialog agent, we need to create a dialog script.
# Below, `flows` is the dialog script.
# A dialog script is a flow dictionary that can contain multiple flows .
# Flows are needed in order to divide a dialog into sub-dialogs and process them separately.
# For example, the separation can be tied to the topic of the dialog.
# In our example, there is one flow called greeting_flow.

# Inside each flow, we can describe a sub-dialog using keyword `GRAPH` from dff.core.keywords module.
# Here we can also use keyword `GLOBAL_TRANSITIONS`, which we have considered in other examples.

# `GRAPH` describes a sub-dialog using linked nodes, each node has the keywords `RESPONSE` and `TRANSITIONS`.

# `RESPONSE` - contains the response that the dialog agent will return when transitioning to this node.
# `TRANSITIONS` - describes transitions from the current node to other nodes.
# `TRANSITIONS` are described in pairs:
#      - the node to which the agent will perform the transition
#      - the condition under which to make the transition


def always_true_condition(ctx: Context, actor: Actor, *args, **kwargs) -> bool:
    return True


flows = {
    "global_flow": {
        GRAPH: {
            "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
                RESPONSE: "",
                TRANSITIONS: {
                    ("music_flow", "node1"): regexp(r"talk about music"),  # first check
                    ("greeting_flow", "node1"): regexp(r"[(hi)(hello)]", re.IGNORECASE),  # second check
                    "fallback_node": always_true_condition,  # third check
                },
            },
            "fallback_node": {  # We get to this node if an error occurred while the agent was running
                RESPONSE: "Ooops",
                TRANSITIONS: {"node1": regexp(r"[(hi)(hello)]", re.IGNORECASE)},
            },
        }
    },
    "greeting_flow": {
        GRAPH: {
            "node1": {
                RESPONSE: "Hi, how are you?",  # When the agent goes to node1, we return "Hi, how are you?"
                TRANSITIONS: {
                    (
                        "global_flow",
                        "fallback_node",
                    ): always_true_condition,
                    "node2": exact_match("i'm fine, how are you?"),
                    # forward(): exact_match("i'm fine, how are you?"),
                    # to_fallback(): always_true_condition,
                },
            },
            "node2": {
                RESPONSE: "Good. What do you want to talk about?",
                TRANSITIONS: {"node3": exact_match("Let's talk about music.")},
            },
            "node3": {
                RESPONSE: "Sorry, I can not talk about music now.",
                TRANSITIONS: {"node4": exact_match("Ok, goodbye.")},
            },
            "node4": {
                RESPONSE: "bye",
                TRANSITIONS: {"node1": exact_match("Hi")},
            },
            "fallback_node": {  # We get to this node if an error occurred while the agent was running
                RESPONSE: "Ooops",
                TRANSITIONS: {"node1": exact_match("Hi")},
            },
        }
    },
    "music_flow": {
        GRAPH: {
            "node1": {
                RESPONSE: "I like music. What genre of music do you like?",
                TRANSITIONS: {"node2": exact_match("i'm fine, how are you?")},
            },
            "node2": {
                RESPONSE: "Good. What do you want to talk about?",
                TRANSITIONS: {"node3": exact_match("Let's talk about music.")},
            },
            "node3": {
                RESPONSE: "Sorry, I can not talk about music now.",
                TRANSITIONS: {"node4": exact_match("Ok, goodbye.")},
            },
            "node4": {
                RESPONSE: "bye",
                TRANSITIONS: {"node1": exact_match("Hi")},
            },
            "fallback_node": {  # We get to this node if an error occurred while the agent was running
                RESPONSE: "Ooops",
                TRANSITIONS: {"node1": exact_match("Hi")},
            },
        }
    },
}
actor = Actor(
    flows,
    start_node_label=("greeting_flow", "start_node"),
    fallback_node_label=("greeting_flow", "fallback_node"),
    default_priority=1.0,  #
)


# testing
testing_dialog = [
    ("Hi", "Hi, how are you?"),  # start_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
    ("Hi", "Hi, how are you?"),  # node4 -> node1
    ("stop", "Ooops"),  # node1 -> fallback_node
    ("one", "Ooops"),  # fallback_node -> fallback_node
    ("help", "Ooops"),  # fallback_node -> fallback_node
    ("nope", "Ooops"),  # fallback_node -> fallback_node
    ({"some_key": "some_value"}, "Hi, how are you?"),  # fallback_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
]


def run_test():
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = example_1_basics.turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


if __name__ == "__main__":
    run_test()
    example_1_basics.run_interactive_mode(actor)
