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
from dff.script.core.message import Button
from dff.messengers.telegram import (
    PollingTelegramInterface,
    TelegramUI,
    TelegramMessage,
)
from dff.messengers.telegram.message import _ClickButton
from dff.utils.testing.common import is_interactive_mode


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
            TRANSITIONS: {
                ("general", "keyboard"): (
                    lambda ctx, actor: ctx.last_request.text in ("/start", "/restart")
                ),
            },
        },
        "fallback": {
            RESPONSE: TelegramMessage(text="Finishing test, send /restart command to restart"),
            TRANSITIONS: {
                ("general", "keyboard"): (
                    lambda ctx, actor: ctx.last_request.text in ("/start", "/restart")
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
                            Button(text="19", payload="correct"),
                            Button(text="21", payload="wrong"),
                        ],
                        is_inline=True,
                    ),
                }
            ),
            TRANSITIONS: {
                ("general", "success"): cnd.exact_match(TelegramMessage(callback_query="correct")),
                ("general", "fail"): cnd.exact_match(TelegramMessage(callback_query="wrong")),
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

happy_path = (
    (
        TelegramMessage(text="/start"),
        TelegramMessage(
            text="Starting test! What's 9 + 10?",
            ui=TelegramUI(
                buttons=[
                    Button(text="19", payload="correct"),
                    Button(text="21", payload="wrong"),
                ],
            ),
        ),
    ),
    (
        TelegramMessage(callback_query=_ClickButton(button_index=1)),
        TelegramMessage(text="Incorrect answer, type anything to try again"),
    ),
    (
        TelegramMessage(text="try again"),
        TelegramMessage(
            text="Starting test! What's 9 + 10?",
            ui=TelegramUI(
                buttons=[
                    Button(text="19", payload="correct"),
                    Button(text="21", payload="wrong"),
                ],
            ),
        ),
    ),
    (
        TelegramMessage(callback_query=_ClickButton(button_index=0)),
        TelegramMessage(text="Success!"),
    ),
    (
        TelegramMessage(text="Yay!"),
        TelegramMessage(text="Finishing test, send /restart command to restart"),
    ),
    (
        TelegramMessage(text="/restart"),
        TelegramMessage(
            text="Starting test! What's 9 + 10?",
            ui=TelegramUI(
                buttons=[
                    Button(text="19", payload="correct"),
                    Button(text="21", payload="wrong"),
                ],
            ),
        ),
    ),
)

interface = PollingTelegramInterface(token=os.getenv("TG_BOT_TOKEN", ""))


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=interface,
)


def main():
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    main()
