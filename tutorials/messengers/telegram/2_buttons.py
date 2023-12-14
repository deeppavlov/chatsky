# %% [markdown]
"""
# Telegram: 2. Buttons

This tutorial shows how to display and hide a basic keyboard in Telegram.

Here, %mddoclink(api,messengers.telegram.message,TelegramMessage)
class is used to represent telegram message,
%mddoclink(api,messengers.telegram.message,TelegramUI) and
%mddoclink(api,messengers.telegram.message,RemoveKeyboard)
classes are used for configuring additional telegram message features.

Different %mddoclink(api,script.core.message,message)
classes are used for representing different common message features,
like Attachment, Audio, Button, Image, etc.
"""


# %pip install dff[telegram]

# %%
import os

import dff.script.conditions as cnd
from dff.script import TRANSITIONS, RESPONSE
from dff.script.core.message import Button
from dff.pipeline import Pipeline
from dff.messengers.telegram import (
    PollingTelegramInterface,
    TelegramUI,
    TelegramMessage,
    RemoveKeyboard,
)
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
            RESPONSE: TelegramMessage(
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
            RESPONSE: TelegramMessage(
                text="Question: What's 2 + 2?",
                # In this case, we use telegram-specific classes.
                # They derive from the generic ones and include more options,
                # e.g. simple keyboard or inline keyboard.
                ui=TelegramUI(
                    buttons=[
                        Button(text="5"),
                        Button(text="4"),
                    ],
                    is_inline=False,
                    row_width=4,
                ),
            ),
            TRANSITIONS: {
                ("general", "success"): cnd.exact_match(
                    TelegramMessage(text="4")
                ),
                ("general", "fail"): cnd.true(),
            },
        },
        "success": {
            RESPONSE: TelegramMessage(
                **{"text": "Success!", "ui": RemoveKeyboard()}
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "fail": {
            RESPONSE: TelegramMessage(
                **{
                    "text": "Incorrect answer, type anything to try again",
                    "ui": RemoveKeyboard(),
                }
            ),
            TRANSITIONS: {("general", "native_keyboard"): cnd.true()},
        },
    },
}

interface = PollingTelegramInterface(token=os.environ["TG_BOT_TOKEN"])

# this variable is only for testing
happy_path = (
    (
        TelegramMessage(text="/start"),
        TelegramMessage(
            text="Question: What's 2 + 2?",
            ui=TelegramUI(
                buttons=[
                    Button(text="5"),
                    Button(text="4"),
                ],
                is_inline=False,
                row_width=4,
            ),
        ),
    ),
    (
        TelegramMessage(text="5"),
        TelegramMessage(
            text="Incorrect answer, type anything to try again",
            ui=RemoveKeyboard(),
        ),
    ),
    (
        TelegramMessage(text="ok"),
        TelegramMessage(
            text="Question: What's 2 + 2?",
            ui=TelegramUI(
                buttons=[
                    Button(text="5"),
                    Button(text="4"),
                ],
                is_inline=False,
                row_width=4,
            ),
        ),
    ),
    (
        TelegramMessage(text="4"),
        TelegramMessage(text="Success!", ui=RemoveKeyboard()),
    ),
    (
        TelegramMessage(text="Yay!"),
        TelegramMessage(
            text="Finishing test, send /restart command to restart"
        ),
    ),
    (
        TelegramMessage(text="/start"),
        TelegramMessage(
            text="Question: What's 2 + 2?",
            ui=TelegramUI(
                buttons=[
                    Button(text="5"),
                    Button(text="4"),
                ],
                is_inline=False,
                row_width=4,
            ),
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
