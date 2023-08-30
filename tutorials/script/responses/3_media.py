# %% [markdown]
"""
# Responses: 3. Media

"""

# %pip install dff

# %%
from dff.script import RESPONSE, TRANSITIONS
from dff.script.conditions import std_conditions as cnd

from dff.script.core.message import Attachments, Image, Message

from dff.pipeline import Pipeline
from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)


# %%
img_url = "https://www.python.org/static/img/python-logo.png"
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
                ("pics", "send_many", 1.0): cnd.regexp(f"{img_url} repeat 10 times"),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
        "send_one": {
            RESPONSE: Message(
                text="here's my picture!", attachments=Attachments(files=[Image(source=img_url)])
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: Message(
                text="Look at my pictures",
                attachments=Attachments(files=[Image(source=img_url)] * 10),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "repeat": {
            RESPONSE: Message(text="I cannot find the picture. Please, try again."),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.regexp(r"^http.+\.png$"),
                ("pics", "send_many", 1.0): cnd.regexp(r"^http.+\.png repeat 10 times"),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
    },
}

happy_path = (
    (Message(text="Hi"), Message(text="Please, send me a picture url")),
    (Message(text="no"), Message(text="I cannot find the picture. Please, try again.")),
    (
        Message(text=img_url),
        Message(text="here's my picture!", attachments=Attachments(files=[Image(source=img_url)])),
    ),
    (Message(text="ok"), Message(text="Final node reached, send any message to restart.")),
    (Message(text="ok"), Message(text="Please, send me a picture url")),
    (
        Message(text=f"{img_url} repeat 10 times"),
        Message(
            text="Look at my pictures",
            attachments=Attachments(files=[Image(source=img_url)] * 10),
        ),
    ),
    (Message(text="ok"), Message(text="Final node reached, send any message to restart.")),
)


# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, happy_path)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
