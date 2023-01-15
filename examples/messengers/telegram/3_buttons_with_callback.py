# %% [markdown]
"""
# 3. Buttons with Callback


This example demonstrates, how to add an inline keyboard and utilize
inline queries.
"""

# %%
import os

import dff.script.conditions as cnd
from dff.script import TRANSITIONS, RESPONSE
from dff.pipeline import Pipeline
from dff.messengers.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
    TelegramUI,
    TelegramButton,
    TelegramMessage,
)
from dff.utils.testing.common import is_interactive_mode


# %%
# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
messenger = TelegramMessenger(token=os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %% [markdown]
"""
If you want to send an inline keyboard to your Telegram chat,
one of the ways is to use the generic `Keyboard` class
that fills the `ui` field of the `Response` class.

Pushing a button of an inline keyboard results in a callback
query being sent to your bot. To process these results,
you need to employ the `callback_query_handler`
in transition conditions (see below).

"""


# %%
script = {
    "root": {
        "start": {
            RESPONSE: TelegramMessage(text="hi"),
            TRANSITIONS: {
                ("general", "keyboard"): cnd.true(),
            },
        },
        "fallback": {
            RESPONSE: TelegramMessage(text="Finishing test, send /restart command to restart"),
            TRANSITIONS: {
                ("general", "keyboard"): messenger.cnd.message_handler(
                    commands=["start", "restart"]
                )
            },
        },
    },
    "general": {
        "keyboard": {
            RESPONSE: TelegramMessage(
                **{
                    "text": "Starting test! What's 9 + 10?",
                    "ui": TelegramUI(
                        buttons=[
                            TelegramButton(text="19", payload="19"),
                            TelegramButton(text="21", payload="21"),
                        ],
                        is_inline=True,
                    ),
                }
            ),
            TRANSITIONS: {
                ("general", "success"): messenger.cnd.callback_query_handler(
                    func=lambda call: call.data == "19"
                ),
                ("general", "fail"): messenger.cnd.callback_query_handler(
                    func=lambda call: call.data == "21"
                ),
            },
        },
        "success": {
            RESPONSE: TelegramMessage(text="Success!"),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "fail": {
            RESPONSE: TelegramMessage(text="Incorrect answer, type anything to try again"),
            TRANSITIONS: {("general", "keyboard"): cnd.true()},
        },
    },
}

interface = PollingTelegramInterface(messenger=messenger)


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
