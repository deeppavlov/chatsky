# %% [markdown]
"""
# 1. Basics

"""


# %%
from typing import NamedTuple

from dff.script import Message
from dff.script.conditions import exact_match
from dff.script import Context, RESPONSE, TRANSITIONS
from dff.pipeline import Pipeline
from dff.utils.testing import check_happy_path, is_interactive_mode, run_interactive_mode


# %%
toy_script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Message(text=""),
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
        "node1": {
            RESPONSE: Message(text="Hi, how are you?"),
            TRANSITIONS: {"node2": exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: Message(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: Message(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": exact_match("Ok, goodbye.")},
        },
        "node4": {
            RESPONSE: Message(text="bye"),
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
        "fallback_node": {
            RESPONSE: Message(text="Ooops"),
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
    }
}

happy_path = (
    (Message(text="Hi"), Message(text="Hi, how are you?")),
    (Message(text="i'm fine, how are you?"), Message(text="Good. What do you want to talk about?")),
    (Message(text="Let's talk about music."), Message(text="Sorry, I can not talk about music now.")),
    (Message(text="Ok, goodbye."), Message(text="bye")),
    (Message(text="Hi"), Message(text="Hi, how are you?")),
    (Message(text="stop"), Message(text="Ooops")),
    (Message(text="stop"), Message(text="Ooops")),
    (Message(text="Hi"), Message(text="Hi, how are you?")),
    (Message(text="i'm fine, how are you?"), Message(text="Good. What do you want to talk about?")),
    (Message(text="Let's talk about music."), Message(text="Sorry, I can not talk about music now.")),
    (Message(text="Ok, goodbye."), Message(text="bye")),
)


# %%
class CallbackRequest(NamedTuple):
    payload: str


def process_request(ctx: Context):
    ui = ctx.last_response and ctx.last_response.ui
    if ui and ctx.last_response.ui.buttons:
        try:
            chosen_button = ui.buttons[int(ctx.last_request)]
        except (IndexError, ValueError):
            raise ValueError(
                "Type in the index of the correct option" "to choose from the buttons."
            )
        ctx.last_request = CallbackRequest(payload=chosen_button.payload)


# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    pre_services=[process_request],
)

if __name__ == "__main__":
    check_happy_path(
        pipeline,
        happy_path,
    )  # This is a function for automatic example running
    # (testing) with `happy_path`

    # This runs example in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs example in interactive mode
