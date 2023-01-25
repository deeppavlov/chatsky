# %% [markdown]
"""
# 2. Buttons


This example shows how to display and hide a basic keyboard in Telegram.
"""

# %%
import os

from telebot import types

import dff.script.conditions as cnd
from dff.script import TRANSITIONS, RESPONSE
from dff.pipeline import Pipeline
from dff.messengers.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
    TelegramUI,
    TelegramMessage,
)
from dff.utils.testing.common import is_interactive_mode


# %%
# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
messenger = TelegramMessenger(token=os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %% [markdown]
"""
To display or hide a keyboard, you can utilize the `TelegramUI` class.
It can be initialized either with the `keyboard` parameter (allows `telebot` keyboards)
or with the `buttons` parameter (the keyboard will be constructed under the hood).

`TelegramUI` should be passed to the `ui` field
of the generic `Response` class.
"""


# %%
script = {
    "root": {
        "start": {
            RESPONSE: TelegramMessage(text="hi"),
            TRANSITIONS: {
                ("general", "native_keyboard"): cnd.true(),
            },
        },
        "fallback": {
            RESPONSE: TelegramMessage(text="Finishing test, send /restart command to restart"),
            TRANSITIONS: {
                ("general", "native_keyboard"): messenger.cnd.message_handler(
                    commands=["start", "restart"]
                )
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
                        TelegramButton(text="5", payload="5"),
                        TelegramButton(text="4", payload="4"),
                    ],
                    is_inline=False,
                    row_width=4,
                ),
            ),
            TRANSITIONS: {
                ("general", "success"): messenger.cnd.message_handler(
                    func=lambda msg: msg.text == "4"
                ),
                ("general", "fail"): cnd.true(),
            },
        },
        "success": {
            RESPONSE: TelegramMessage(
                **{"text": "Success!", "ui": TelegramUI(keyboard=types.ReplyKeyboardRemove())}
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "fail": {
            RESPONSE: TelegramMessage(
                **{
                    "text": "Incorrect answer, type anything to try again",
                    "ui": TelegramUI(keyboard=types.ReplyKeyboardRemove()),
                }
            ),
            TRANSITIONS: {("general", "native_keyboard"): cnd.true()},
        },
    },
}

interface = PollingTelegramInterface(messenger=messenger)


happy_path = (
    ("hi", "Question: What's 2 + 2?"),
    ("5", "Incorrect answer, type anything to try again"),
    ("ok", "Question: What's 2 + 2?"),
    ("4", "Success!"),
)


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=interface,
)


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    pipeline.run()
