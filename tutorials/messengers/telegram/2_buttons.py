# %% [markdown]
"""
# Telegram: 2. Buttons

This tutorial shows how to display and hide a basic keyboard in Telegram.

Different %mddoclink(api,script.core.message,message)
classes are used for representing different common message features,
like Attachment, Audio, Button, Image, etc.
"""


# %pip install dff[telegram]

# %%
import os

import dff.script.conditions as cnd
from dff.script import TRANSITIONS, RESPONSE
from dff.script.core.message import Button, Keyboard, Message
from dff.pipeline import Pipeline
from dff.messengers.telegram import PollingTelegramInterface
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
To display or hide a keyboard, you can utilize the `ui` field of the
`TelegramMessage` class. It can be initialized either with
a `TelegramUI` instance or with a custom telebot keyboard.

Passing an instance of `RemoveKeyboard` to the `ui` field
will indicate that the keyboard should be removed.
"""


# %%
script = {
    "root": {
        "start": {
            TRANSITIONS: {
                ("general", "native_keyboard"): (
                    lambda ctx, _: ctx.last_request.text
                    in ("/start", "/restart")
                ),
            },
        },
        "fallback": {
            RESPONSE: Message(
                text="Finishing test, send /restart command to restart"
            ),
            TRANSITIONS: {
                ("general", "native_keyboard"): (
                    lambda ctx, _: ctx.last_request.text
                    in ("/start", "/restart")
                ),
            },
        },
    },
    "general": {
        "native_keyboard": {
            RESPONSE: Message(
                text="Question: What's 2 + 2?",
                attachments=[
                    Keyboard(
                        buttons=[
                            [
                                Button(text="5"),
                                Button(text="4"),
                            ],
                        ],
                    ),
                ],
            ),
            TRANSITIONS: {
                ("general", "success"): cnd.has_callback_query("4"),
                ("general", "fail"): cnd.true(),
            },
        },
        "success": {
            RESPONSE: Message(text="Success!"),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "fail": {
            RESPONSE: Message(
                text="Incorrect answer, type anything to try again"
            ),
            TRANSITIONS: {("general", "native_keyboard"): cnd.true()},
        },
    },
}

interface = PollingTelegramInterface(token=os.environ["TG_BOT_TOKEN"])

# this variable is only for testing
happy_path = (
    (
        Message(text="/start"),
        Message(
            text="Question: What's 2 + 2?",
            attachments=[
                Keyboard(
                    buttons=[
                        [
                            Button(text="5"),
                            Button(text="4"),
                        ],
                    ],
                ),
            ],
        ),
    ),
    (
        Message(text="5"),
        Message(text="Incorrect answer, type anything to try again"),
    ),
    (
        Message(text="ok"),
        Message(
            text="Question: What's 2 + 2?",
            attachments=[
                Keyboard(
                    buttons=[
                        [
                            Button(text="5"),
                            Button(text="4"),
                        ],
                    ],
                ),
            ],
        ),
    ),
    (
        Message(text="4"),
        Message(text="Success!"),
    ),
    (
        Message(text="Yay!"),
        Message(text="Finishing test, send /restart command to restart"),
    ),
    (
        Message(text="/start"),
        Message(
            text="Question: What's 2 + 2?",
            attachments=[
                Keyboard(
                    buttons=[
                        [
                            Button(text="5"),
                            Button(text="4"),
                        ],
                    ],
                ),
            ],
        ),
    ),
)


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=interface,
)


def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
