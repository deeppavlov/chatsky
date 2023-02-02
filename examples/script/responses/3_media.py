# %% [markdown]
"""
# 3. Media

"""


# %%
from typing import NamedTuple

from dff.script import Context, RESPONSE, TRANSITIONS
from dff.script.conditions import std_conditions as cnd

from dff.script.core.message import Attachments, Image, Message

from dff.pipeline import Pipeline
from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)


# %%
# kitten picture info:
kitten_id = "Y0WXj3xqJz0"
kitten_ixid = "MnwxMjA3fDB8MXxhbGx8fHx8fHx8fHwxNjY4NjA2NTI0"
kitten_width = 640
kitten_url = (
    f"https://unsplash.com/photos/"
    f"{kitten_id}/download?ixid={kitten_ixid}"
    f"&force=true&w={kitten_width}"
)

toy_script = {
    "root": {
        "start": {
            RESPONSE: Message(text=""),
            TRANSITIONS: {("pics", "ask_picture"): cnd.true()},
        },
        "fallback": {
            RESPONSE: Message(text="Final node reached, send any message to restart."),
            TRANSITIONS: {("pics", "ask_picture"): cnd.true()},
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: Message(text="Please, send me a picture url"),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.regexp(r"^http.+\.png$"),
                ("pics", "send_many", 1.0): cnd.regexp(r"^http.+\.jpg$"),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
        "send_one": {
            RESPONSE: Message(
                text="here's my picture!", attachments=Attachments(files=[Image(source=kitten_url)])
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: Message(
                text="Look at my pictures",
                attachments=Attachments(files=[Image(source=kitten_url)] * 10),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "repeat": {
            RESPONSE: Message(text="I cannot find the picture. Please, try again."),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.regexp(r"^http.+\.png$"),
                ("pics", "send_many", 1.0): cnd.regexp(r"^http.+\.jpg$"),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
    },
}

happy_path = (
    (Message(text="Hi"), Message(text="Please, send me a picture url")),
    (Message(text="no"), Message(text="I cannot find the picture. Please, try again.")),
    (
        Message(text="https://sun9-49.userapi.com/s/v1/if2/gpquN.png"),
        Message(
            text="here's my picture!", attachments=Attachments(files=[Image(source=kitten_url)])
        ),
    ),
    (Message(text="ok"), Message(text="Final node reached, send any message to restart.")),
    (Message(text="ok"), Message(text="Please, send me a picture url")),
    (
        Message(text="https://sun9-49.userapi.com/s/v1/if2/gpquN.jpg"),
        Message(
            text="Look at my pictures",
            attachments=Attachments(files=[Image(source=kitten_url)] * 10),
        ),
    ),
    (Message(text="ok"), Message(text="Final node reached, send any message to restart.")),
)


# %%
class CallbackRequest(NamedTuple):
    payload: str


def process_request(ctx: Context):
    ui = ctx.last_response and ctx.last_response.ui
    if ui and ctx.last_response.ui.buttons:
        try:
            chosen_button = ui.buttons[int(ctx.last_request.text)]
        except (IndexError, ValueError):
            raise ValueError("Type in the index of the correct option to choose from the buttons.")
        ctx.last_request = CallbackRequest(payload=chosen_button.payload)


# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    pre_services=[process_request],
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
