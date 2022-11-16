from typing import NamedTuple

from dff.core.engine.core import Context
from dff.core.engine.core.context import get_last_index
from dff.core.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, is_interactive_mode, run_interactive_mode
from dff.utils.testing.toy_script import TOY_SCRIPT

happy_path = (
    ("Hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),
    ("Hi", "Hi, how are you?"),
    ("stop", "Ooops"),
    ("stop", "Ooops"),
    ("Hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),
)


class CallbackRequest(NamedTuple):
    payload: str


def process_request(ctx: Context):
    last_request: str = ctx.last_request  # TODO: add _really_ nice ways to modify user request and response
    last_index = get_last_index(ctx.requests)

    ui = ctx.last_response and ctx.last_response.ui
    if ui and ctx.last_response.ui.buttons:
        try:
            chosen_button = ui.buttons[int(last_request)]
        except (IndexError, ValueError):
            raise ValueError("Type in the index of the correct option to choose from the buttons.")
        ctx.requests[last_index] = CallbackRequest(payload=chosen_button.payload)
        return
    ctx.requests[last_index] = last_request


pipeline = Pipeline.from_script(
    TOY_SCRIPT,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    pre_services=[process_request],
)

if __name__ == "__main__":  # TODO: FIXME: WHAT IS GOING ON HERE??👀
    check_happy_path(
        pipeline,
        happy_path,
    )  # This is a function for automatic example running (testing) with `happy_path`

    # This runs example in interactive mode if not in IPython env + if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs example in interactive mode
