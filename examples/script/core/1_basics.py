# %% [markdown]
"""
# 1. Basics

This notebook shows basic example of creating a simple dialog bot (agent).
Let's do all the necessary imports from `dff`:
"""


# %%
from dff.script import Actor, TRANSITIONS, RESPONSE, Message
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
In this example there is one flow called `greeting_flow`.

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
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Hi"))},
            # If "Hi" == request of the user then we make the transition.
        },
        "node1": {
            RESPONSE: Message(text="Hi, how are you?"),  # When the agent enters node1,
            # return "Hi, how are you?".
            TRANSITIONS: {"node2": cnd.exact_match(Message(text="I'm fine, how are you?"))},
        },
        "node2": {
            RESPONSE: Message(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": cnd.exact_match(Message(text="Let's talk about music."))},
        },
        "node3": {
            RESPONSE: Message(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": cnd.exact_match(Message(text="Ok, goodbye."))},
        },
        "node4": {
            RESPONSE: Message(text="Bye"),
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Hi"))},
        },
        "fallback_node": {
            # We get to this node if the conditions
            # for switching to other nodes are not performed.
            RESPONSE: Message(text="Ooops"),
            TRANSITIONS: {"node1": cnd.exact_match(Message(text="Hi"))},
        },
    }
}


happy_path = (
    (Message(text="Hi"), Message(text="Hi, how are you?")),  # start_node -> node1
    (
        Message(text="I'm fine, how are you?"),
        Message(text="Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message(text="Let's talk about music."),
        Message(text="Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message(text="Ok, goodbye."), Message(text="Bye")),  # node3 -> node4
    (Message(text="Hi"), Message(text="Hi, how are you?")),  # node4 -> node1
    (Message(text="stop"), Message(text="Ooops")),  # node1 -> fallback_node
    (Message(text="stop"), Message(text="Ooops")),  # fallback_node -> fallback_node
    (Message(text="Hi"), Message(text="Hi, how are you?")),  # fallback_node -> node1
    (
        Message(text="I'm fine, how are you?"),
        Message(text="Good. What do you want to talk about?"),
    ),  # node1 -> node2
    (
        Message(text="Let's talk about music."),
        Message(text="Sorry, I can not talk about music now."),
    ),  # node2 -> node3
    (Message(text="Ok, goodbye."), Message(text="Bye")),  # node3 -> node4
)


# %% [markdown]
"""
An `actor` is an object that processes user
inputs and returns responses.
To create the actor you need to pass the script (`toy_script`),
initial node (`start_label`) and
the node to which the actor will default
if none of the current conditions are met (`fallback_label`).
By default, if `fallback_label` is not set,
then its value becomes equal to `start_label`.
"""


# %%
actor = Actor(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

# %% [markdown]
"""
`Actor` is a low-level API way of working with `dff`.
We recommend going the other way and using `Pipeline`,
which has the same functionality but a high-level API.
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
    )  # This is a function for automatic example
    # running (testing example) with `happy_path`.

    # Run example in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set.
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs example in interactive mode.
