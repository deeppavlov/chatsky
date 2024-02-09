# %% [markdown]
"""
# Responses: 3. Media

Here, %mddoclink(api,script.core.message,Attachments) class is shown.
Attachments can be used for attaching different media elements
(such as %mddoclink(api,script.core.message,Image),
%mddoclink(api,script.core.message,Document)
or %mddoclink(api,script.core.message,Audio)).

They can be attached to any message but will only work if the chosen
[messenger interface](%doclink(api,index_messenger_interfaces)) supports them.
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
            RESPONSE: Message(""),
            TRANSITIONS: {("pics", "ask_picture"): cnd.true()},
        },
        "fallback": {
            RESPONSE: Message(
                text="Final node reached, send any message to restart."
            ),
            TRANSITIONS: {("pics", "ask_picture"): cnd.true()},
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: Message("Please, send me a picture url"),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.regexp(r"^http.+\.png$"),
                ("pics", "send_many", 1.0): cnd.regexp(
                    f"{img_url} repeat 10 times"
                ),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
        "send_one": {
            RESPONSE: Message(
                text="here's my picture!",
                attachments=Attachments(files=[Image(source=img_url)]),
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
            RESPONSE: Message(
                text="I cannot find the picture. Please, try again."
            ),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.regexp(r"^http.+\.png$"),
                ("pics", "send_many", 1.0): cnd.regexp(
                    r"^http.+\.png repeat 10 times"
                ),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
    },
}

happy_path = (
    (Message("Hi"), Message("Please, send me a picture url")),
    (
        Message("no"),
        Message("I cannot find the picture. Please, try again."),
    ),
    (
        Message(img_url),
        Message(
            text="here's my picture!",
            attachments=Attachments(files=[Image(source=img_url)]),
        ),
    ),
    (
        Message("ok"),
        Message("Final node reached, send any message to restart."),
    ),
    (Message("ok"), Message("Please, send me a picture url")),
    (
        Message(f"{img_url} repeat 10 times"),
        Message(
            text="Look at my pictures",
            attachments=Attachments(files=[Image(source=img_url)] * 10),
        ),
    ),
    (
        Message("ok"),
        Message("Final node reached, send any message to restart."),
    ),
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
