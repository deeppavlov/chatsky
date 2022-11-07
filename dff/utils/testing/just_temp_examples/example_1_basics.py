"""
1. Basics
=========
"""

# TODO:
# 1. The illustration should express only what is shown in the example, not all at once.
#    Complicate illustrations from one example to another.
# 2. Fix PRE_RESPONSE_PROCESSING to PRE_TRANSITIONS_PROCESSING
# 3. Specify that the nodes form an ordered set

import logging

from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE
from dff.core.engine.core import Actor
import dff.core.engine.conditions as cnd
from dff.core.pipeline.pipeline.pipeline import Pipeline
from dff.utils.common import run_example

logger = logging.getLogger(__name__)

# First of all, to create a dialog agent, we need to create a dialog script.
# Below, `script` is the dialog script.
# A dialog script is a flow dictionary that can contain multiple script .
# Script are needed in order to divide a dialog into sub-dialogs and process them separately.
# For example, the separation can be tied to the topic of the dialog.
# In our example, there is one flow called greeting_flow.

# Inside each flow, we can describe a sub-dialog.
# Here we can also use keyword `LOCAL`, which we have considered in other examples.

# Flow describes a sub-dialog using linked nodes, each node has the keywords `RESPONSE` and `TRANSITIONS`.

# `RESPONSE` - contains the response that the dialog agent will return when transitioning to this node.
# `TRANSITIONS` - describes transitions from the current node to other nodes.
# `TRANSITIONS` are described in pairs:
#      - the node to which the agent will perform the transition
#      - the condition under which to make the transition
script = {
    "greeting_flow": {
        "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},  # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: "Hi, how are you?",  # When the agent goes to node1, we return "Hi, how are you?"
            TRANSITIONS: {"node2": cnd.exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": cnd.exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")},
        },
        "node4": {RESPONSE: "bye", TRANSITIONS: {"node1": cnd.exact_match("Hi")}},
        "fallback_node": {  # We get to this node if an error occurred while the agent was running
            RESPONSE: "Ooops",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
    }
}

# An actor is an object that processes user input replicas and returns responses
# To create the actor, you need to pass the script of the dialogue `script`
# And pass the initial node `start_label`
# and the node to which the actor will go in case of an error `fallback_label`
# If `fallback_label` is not set, then its value becomes equal to `start_label` by default
actor = Actor(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))

# testing
happy_path = [
    ("Hi", "Hi, how are you?"),  # start_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
    ("Hi", "Hi, how are you?"),  # node4 -> node1
    ("stop", "Ooops"),  # node1 -> fallback_node
    ("stop", "Ooops"),  # fallback_node -> fallback_node
    ("Hi", "Hi, how are you?"),  # fallback_node -> node1
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about music now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
]

pipeline = Pipeline.from_script(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode(): # TODO: Add comments about DISABLE_INTERACTIVE_MODE variable
        run_interactive_mode(pipeline)
