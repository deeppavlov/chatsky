# %% [markdown]
"""
# Responses: 1. Basics

Here, the process of response forming is shown.
Special keywords %mddoclink(api,script.core.keywords,Keywords.RESPONSE)
and %mddoclink(api,script.core.keywords,Keywords.TRANSITIONS)
are used for that.
"""

# %pip install dff

# %%
from typing import NamedTuple

from dff.script import Message
from dff.script.conditions import exact_match
from dff.script import RESPONSE, TRANSITIONS
from dff.pipeline import Pipeline
from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)


# %%
toy_script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(""),
            TRANSITIONS: {"node1": exact_match(Message("Hi"))},
        },
        "node1": {
            RESPONSE: Message("Hi, how are you?"),
            TRANSITIONS: {
                "node2": exact_match(Message("i'm fine, how are you?"))
            },
        },
        "node2": {
            RESPONSE: Message("Good. What do you want to talk about?"),
            TRANSITIONS: {
                "node3": exact_match(Message("Let's talk about music."))
            },
        },
        "node3": {
            RESPONSE: Message("Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": exact_match(Message("Ok, goodbye."))},
        },
        "node4": {
            RESPONSE: Message("bye"),
            TRANSITIONS: {"node1": exact_match(Message("Hi"))},
        },
        "fallback_node": {
            RESPONSE: Message("Ooops"),
            TRANSITIONS: {"node1": exact_match(Message("Hi"))},
        },
    }
}

happy_path = (
    (Message("Hi"), Message("Hi, how are you?")),
    (
        Message("i'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),
    (Message("Ok, goodbye."), Message("bye")),
    (Message("Hi"), Message("Hi, how are you?")),
    (Message("stop"), Message("Ooops")),
    (Message("stop"), Message("Ooops")),
    (Message("Hi"), Message("Hi, how are you?")),
    (
        Message("i'm fine, how are you?"),
        Message("Good. What do you want to talk about?"),
    ),
    (
        Message("Let's talk about music."),
        Message("Sorry, I can not talk about music now."),
    ),
    (Message("Ok, goodbye."), Message("bye")),
)


# %%
class CallbackRequest(NamedTuple):
    payload: str


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
    )  # This is a function for automatic tutorial running
    # (testing) with `happy_path`

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
