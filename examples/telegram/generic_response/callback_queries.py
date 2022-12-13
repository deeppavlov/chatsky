"""
Callback Queries
=================

This example shows how to use generic classes from dff.

Here, we use Telegram API's callback queries and buttons.
"""
import os

from telebot import types

import dff.core.engine.conditions as cnd
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE
from dff.core.pipeline import Pipeline
from dff.connectors.messenger.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
    TelegramUI,
    TelegramButton,
)
from dff.connectors.messenger.generics import Response, Keyboard, Button
from dff.utils.testing.common import is_interactive_mode, run_interactive_mode

# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
messenger = TelegramMessenger(token=os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))

"""
The replies below use generic classes.

You can use both generic (`Keyboard`) and telegram-specific (`TelegramUI`) classes.

`Keyboard` does not include all the options that are available in Telegram,
so an InlineKeyboard (see Telegram API) will be created by default.

`TelegramUI` gives you more freedom in terms of managing the interface.
You can configure the keyboard type using the parameter `is_inline`.

If you want to remove the reply keyboard, pass an instance of telebot's `ReplyKeyboardRemove`
to the `TelegramUI` class as the `keyboard` parameter (see below).
"""

script = {
    "root": {
        "start": {
            RESPONSE: Response(text="hi"),
            TRANSITIONS: {
                ("general", "keyboard"): cnd.true(),
            },
        },
        "fallback": {
            RESPONSE: Response(text="Finishing test, send /restart command to restart"),
            TRANSITIONS: {
                ("general", "keyboard"): messenger.cnd.message_handler(
                    commands=["start", "restart"]
                )
            },
        },
    },
    "general": {
        "keyboard": {
            RESPONSE: Response(
                **{
                    "text": "Starting test! What's 9 + 10?",
                    # Here, we use a generic keyboard class.
                    # Compare with the next script node.
                    "ui": Keyboard(
                        buttons=[Button(text="19", payload="19"), Button(text="21", payload="21")]
                    ),
                }
            ),
            TRANSITIONS: {
                ("general", "native_keyboard"): messenger.cnd.callback_query_handler(
                    func=lambda call: call.data == "19"
                ),
                ("general", "fail"): messenger.cnd.callback_query_handler(
                    func=lambda call: call.data == "21"
                ),
            },
        },
        "native_keyboard": {
            RESPONSE: Response(
                **{
                    "text": "Question: What's 2 + 2?",
                    # In this case, we use telegram-specific classes.
                    # They derive from the generic ones and include more options,
                    # e.g. simple keyboard or inline keyboard.
                    "ui": TelegramUI(
                        buttons=[
                            TelegramButton(text="5", payload="5"),
                            TelegramButton(text="4", payload="4"),
                        ],
                        is_inline=False,
                        row_width=4,
                    ),
                }
            ),
            TRANSITIONS: {
                ("general", "success", 1.2): messenger.cnd.message_handler(
                    func=lambda msg: msg.text == "4"
                ),
                ("general", "fail", 1.0): cnd.true(),
            },
        },
        "success": {
            RESPONSE: Response(
                **{"text": "Success!", "ui": TelegramUI(keyboard=types.ReplyKeyboardRemove())}
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "fail": {
            RESPONSE: Response(
                **{
                    "text": "Incorrect answer, type anything to try again",
                    "ui": TelegramUI(keyboard=types.ReplyKeyboardRemove()),
                }
            ),
            TRANSITIONS: {("general", "keyboard"): cnd.true()},
        },
    },
}

interface = PollingTelegramInterface(messenger=messenger)

pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    context_storage=dict(),
    messenger_interface=interface,
)

if __name__ == "__main__":
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    elif is_interactive_mode():
        run_interactive_mode(pipeline)  # run in an interactive shell
    else:
        pipeline.run()  # run in telegram
