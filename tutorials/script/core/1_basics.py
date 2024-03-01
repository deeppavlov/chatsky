# %% [markdown]
"""
# Core: 1. Basics

This notebook shows basic tutorial of creating a simple dialog bot (agent).

Here, basic usege of %mddoclink(api,pipeline.pipeline.pipeline,Pipeline)
primitive is shown: its' creation with
%mddoclink(api,pipeline.pipeline.pipeline,Pipeline.from_script)
and execution.

Additionally, function %mddoclink(api,utils.testing.common,check_happy_path)
that can be used for Pipeline testing is presented.

Let's do all the necessary imports from DFF:
"""

# %pip install dff

# %%
from dff.script import TRANSITIONS, RESPONSE, Message
from dff.pipeline import Pipeline
import dff.script.conditions as cnd

from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)


# %% [markdown]
"""
First of all, to create a dialog agent, we need to create a dialog script.
Below script means a dialog script.
A script is a dictionary, where the keys are the names of the flows.
A script can contain multiple scripts, which is needed in order to divide
a dialog into sub-dialogs and process them separately.
For example, the separation can be tied to the topic of the dialog.
In this tutorial there is one flow called `greeting_flow`.

Flow describes a sub-dialog using linked nodes.
Each node has the keywords `RESPONSE` and `TRANSITIONS`.

* `RESPONSE` contains the response
    that the agent will return from the current node.
* `TRANSITIONS` describes transitions from the
    current node to another nodes. This is a dictionary,
    where keys are names of the nodes and
    values are conditions of transition to them.
"""


# %%
toy_script = {
    "greeting_flow": {
        "start_node": {  # This is the initial node,
            # it doesn't contain a `RESPONSE`.
            RESPONSE: Message(),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
            # If "Hi" == request of the user then we make the transition.
        },
        "node1": {
            RESPONSE: Message(
                text="Hi, how are you?"
            ),  # When the agent enters node1,
            # return "Hi, how are you?".
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
            RESPONSE: Message("Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": cnd.exact_match(Message("Ok, goodbye."))},
        },
        "node4": {
            RESPONSE: Message("Bye"),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
        },
        "fallback_node": {
            # We get to this node if the conditions
            # for switching to other nodes are not performed.
            RESPONSE: Message("Ooops"),
            TRANSITIONS: {"node1": cnd.exact_match(Message("Hi"))},
        },
    }
}


happy_path = (
    (
        Message("Hi"),
        Message("Hi, how are you?"),
    ),  # start_node -> node1
    (
        Message("I'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("Bye")),  # node3 -> node4
    (Message("Hi"), Message("Hi, how are you?")),  # node4 -> node1
    (Message("stop"), Message("Ooops")),  # node1 -> fallback_node
    (
        Message("stop"),
        Message("Ooops"),
    ),  # fallback_node -> fallback_node
    (
        Message("Hi"),
        Message("Hi, how are you?"),
    ),  # fallback_node -> node1
    (
        Message("I'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message("Ok, goodbye."), Message("Bye")),  # node3 -> node4
)


# %% [markdown]
"""
A `Pipeline` is an object that processes user
inputs and returns responses.
To create the pipeline you need to pass the script (`toy_script`),
initial node (`start_label`) and
the node to which the default transition will take place
if none of the current conditions are met (`fallback_label`).
By default, if `fallback_label` is not set,
then its value becomes equal to `start_label`.
"""


# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

if __name__ == "__main__":
    check_happy_path(
        pipeline,
        happy_path,
    )  # This is a function for automatic tutorial
    # running (testing tutorial) with `happy_path`.

    # Run tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set.
    if is_interactive_mode():
        run_interactive_mode(pipeline)
        # This runs tutorial in interactive mode.
