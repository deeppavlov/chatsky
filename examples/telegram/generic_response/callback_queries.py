"""
The replies below use generic classes.
When creating a UI, you can use the generic Keyboard class.
It does not include all the options that are available in Telegram, so an InlineKeyboard will be created by default.
If you want to remove the reply keyboard, pass an instance of telebot's ReplyKeyboardRemove
to the TelegramUI class.
"""
import logging
import os

import dff.core.engine.conditions as cnd
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from telebot import types

from dff.connectors.messenger.telegram.connector import TelegramConnector
from dff.connectors.messenger.telegram.types import TelegramUI, TelegramButton
from dff.connectors.messenger.telegram.interface import PollingTelegramInterface
from dff.core.pipeline import Pipeline

from dff.connectors.messenger.generics import Response, Keyboard, Button
from examples.telegram._telegram_utils import check_env_bot_tokens, get_auto_arg, auto_run_pipeline

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

bot = TelegramConnector(token=os.getenv("BOT_TOKEN", "SOMETOKEN"))


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
            TRANSITIONS: {("general", "keyboard"): bot.cnd.message_handler(commands=["start", "restart"])},
        },
    },
    "general": {
        "keyboard": {
            RESPONSE: Response(
                **{
                    "text": "Starting test! What's 9 + 10?",
                    # Here, we use a generic keyboard class that will be compatible with any other dff add-on.
                    # Compare with the next script node.
                    "ui": Keyboard(buttons=[Button(text="19", payload="19"), Button(text="21", payload="21")]),
                }
            ),
            TRANSITIONS: {
                ("general", "native_keyboard"): bot.cnd.callback_query_handler(func=lambda call: call.data == "19"),
                ("general", "fail"): bot.cnd.callback_query_handler(func=lambda call: call.data == "21"),
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
                        buttons=[TelegramButton(text="5", payload="5"), TelegramButton(text="4", payload="4")],
                        is_inline=False,
                        row_width=4,
                    ),
                }
            ),
            TRANSITIONS: {
                ("general", "success", 1.2): bot.cnd.message_handler(func=lambda msg: msg.text == "4"),
                ("general", "fail", 1.0): cnd.true(),
            },
        },
        "success": {
            RESPONSE: Response(**{"text": "Success!", "ui": TelegramUI(keyboard=types.ReplyKeyboardRemove())}),
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

interface = PollingTelegramInterface(bot=bot)

pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    context_storage=dict(),
    messenger_interface=interface,
)

if __name__ == "__main__":
    check_env_bot_tokens()
    if get_auto_arg():
        auto_run_pipeline(pipeline, logger=logger)
    else:
        pipeline.run()
