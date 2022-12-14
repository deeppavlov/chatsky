# %% [markdown]
"""
# 1. Basics

"""


# %%
from typing import NamedTuple

from dff.script.responses import Response
from dff.script.conditions import exact_match
from dff.script import Context, get_last_index, RESPONSE, TRANSITIONS
from dff.pipeline import Pipeline
from dff.utils.testing import check_happy_path, is_interactive_mode, run_interactive_mode


# %%
toy_script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Response(text=""),
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
        "node1": {
            RESPONSE: Response(text="Hi, how are you?"),
            TRANSITIONS: {"node2": exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: Response(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: Response(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": exact_match("Ok, goodbye.")},
        },
        "node4": {
            RESPONSE: Response(text="bye"),
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
        "fallback_node": {
            RESPONSE: Response(text="Ooops"),
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
    }
}

happy_path = (
    ("Hi", Response(text="Hi, how are you?")),
    ("i'm fine, how are you?", Response(text="Good. What do you want to talk about?")),
    ("Let's talk about music.", Response(text="Sorry, I can not talk about music now.")),
    ("Ok, goodbye.", Response(text="bye")),
    ("Hi", Response(text="Hi, how are you?")),
    ("stop", Response(text="Ooops")),
    ("stop", Response(text="Ooops")),
    ("Hi", Response(text="Hi, how are you?")),
    ("i'm fine, how are you?", Response(text="Good. What do you want to talk about?")),
    ("Let's talk about music.", Response(text="Sorry, I can not talk about music now.")),
    ("Ok, goodbye.", Response(text="bye")),
)


# %%
class CallbackRequest(NamedTuple):
    payload: str


def process_request(ctx: Context):
    last_request: str = ctx.last_request
    last_index = get_last_index(ctx.requests)

    ui = ctx.last_response and ctx.last_response.ui
    if ui and ctx.last_response.ui.buttons:
        try:
            chosen_button = ui.buttons[int(last_request)]
        except (IndexError, ValueError):
            raise ValueError(
                "Type in the index of the correct option" "to choose from the buttons."
            )
        ctx.requests[last_index] = CallbackRequest(payload=chosen_button.payload)
        return
    ctx.requests[last_index] = last_request


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
