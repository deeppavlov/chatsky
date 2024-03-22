# %% [markdown]
"""
# Telegram: 3. Buttons with Callback

This tutorial demonstrates, how to add an inline keyboard and utilize
inline queries.

Different %mddoclink(api,script.core.message,message)
classes are used for representing different common message features,
like Attachment, Audio, Button, Image, etc.
"""


# %pip install dff[telegram]

# %%
import os

import dff.script.conditions as cnd
from dff.script import TRANSITIONS, RESPONSE
from dff.pipeline import Pipeline
from dff.script.core.message import Button, Keyboard, Message
from dff.messengers.telegram import PollingTelegramInterface
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
If you want to send an inline keyboard to your Telegram chat,
set `is_inline` field of the `TelegramUI` instance to `True`
(note that it is inline by default, so you could also omit it).

Pushing a button of an inline keyboard results in a callback
query being sent to your bot. The data of the query
is stored in the `callback_query` field of a user `TelegramMessage`.
"""


# %%
script = {
    "root": {
        "start": {
            TRANSITIONS: {
                ("general", "keyboard"): (
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
                ("general", "keyboard"): (
                    lambda ctx, _: ctx.last_request.text
                    in ("/start", "/restart")
                )
            },
        },
    },
    "general": {
        "keyboard": {
            RESPONSE: Message(
                text="Starting test! What's 9 + 10?",
                attachments=[
                    Keyboard(
                        buttons=[
                            [
                                Button(text="19", data="correct"),
                                Button(text="21", data="wrong"),
                            ],
                        ],
                    ),
                ],
            ),
            TRANSITIONS: {
                ("general", "success"): cnd.has_callback_query("correct"),
                ("general", "fail"): cnd.has_callback_query("wrong"),
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
            TRANSITIONS: {("general", "keyboard"): cnd.true()},
        },
    },
}

# this variable is only for testing
happy_path = (
    (
        Message(text="/start"),
        Message(
            text="Starting test! What's 9 + 10?",
            attachments=[
                Keyboard(
                    buttons=[
                        [
                            Button(text="19", data="correct"),
                            Button(text="21", data="wrong"),
                        ],
                    ],
                ),
            ],
        ),
    ),
    (
        Message(text="wrong"),
        Message(text="Incorrect answer, type anything to try again"),
    ),
    (
        Message(text="try again"),
        Message(
            text="Starting test! What's 9 + 10?",
            attachments=[
                Keyboard(
                    buttons=[
                        [
                            Button(text="19", data="correct"),
                            Button(text="21", data="wrong"),
                        ],
                    ],
                ),
            ],
        ),
    ),
    (
        Message(text="correct"),
        Message(text="Success!"),
    ),
    (
        Message(text="Yay!"),
        Message(text="Finishing test, send /restart command to restart"),
    ),
    (
        Message(text="/restart"),
        Message(
            text="Starting test! What's 9 + 10?",
            attachments=[
                Keyboard(
                    buttons=[
                        [
                            Button(text="19", data="correct"),
                            Button(text="21", data="wrong"),
                        ],
                    ],
                ),
            ],
        ),
    ),
)

interface = PollingTelegramInterface(token=os.environ["TG_BOT_TOKEN"])


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
