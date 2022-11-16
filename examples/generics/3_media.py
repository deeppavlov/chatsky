import pathlib
from typing import NamedTuple

from dff.core.engine.core import Context
from dff.core.engine.core.context import get_last_index
from dff.core.engine.core.keywords import RESPONSE, TRANSITIONS
from dff.core.engine import conditions as cnd

from dff.connectors.messenger.generics.response import Attachments, Image, Response

from dff.core.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, is_interactive_mode, run_interactive_mode
from dff.utils.testing.response_comparers import generics_diff

kitten_url = "https://unsplash.com/photos/Y0WXj3xqJz0/download?ixid=MnwxMjA3fDB8MXxhbGx8fHx8fHx8fHwxNjY4NjA2NTI0&force=true&w=640"

toy_script = {
    "root": {
        "start": {
            RESPONSE: Response(text=""),
            TRANSITIONS: {("pics", "ask_picture"): cnd.true()},
        },
        "fallback": {
            RESPONSE: Response(text="Final node reached, send any message to restart."),
            TRANSITIONS: {("pics", "ask_picture"): cnd.true()},
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: Response(text="Please, send me a picture url"),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.regexp(r"^http.+\.png$"),
                ("pics", "send_many", 1.0): cnd.regexp(r"^http.+\.jpg$"),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
        "send_one": {
            RESPONSE: Response(
                text="here's my picture!", image=Image(source=kitten_url)
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: Response(
                text="Look at my pictures",
                attachments=Attachments(files=[Image(source=kitten_url)] * 10),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "repeat": {
            RESPONSE: Response(text="I cannot find the picture. Please, try again."),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.regexp(r"^http.+\.png$"),
                ("pics", "send_many", 1.0): cnd.regexp(r"^http.+\.jpg$"),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
    },
}

happy_path = (
    ("Hi", "Please, send me a picture url"),
    ("no", "I cannot find the picture. Please, try again."),
    ("https://sun9-49.userapi.com/s/v1/if2/gpquN.png", "\nhere's my picture!\nAttachment size: 51706 bytes."),
    ("ok", "Final node reached, send any message to restart."),
    ("ok", "Please, send me a picture url"),
    ("https://sun9-49.userapi.com/s/v1/if2/gpquN.jpg", "\nLook at my pictures\nGrouped attachment size: 517060 bytes."),
    ("ok", "Final node reached, send any message to restart."),
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
    toy_script, start_label=("root", "start"), fallback_label=("root", "fallback"), pre_services=[process_request]
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path, generics_diff)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
