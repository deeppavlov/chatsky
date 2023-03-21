# %% [markdown]
"""
# Telegram: 10. No Pipeline Advanced

This tutorial demonstrates how to connect to Telegram without the `pipeline` API.

This shows how you can integrate command and button reactions into your script.
As in other cases, you only need one handler, since the logic is handled by the actor
and the script.
"""


# %%
import os

import dff.script.conditions as cnd
from dff.script import Context, Actor, TRANSITIONS, RESPONSE

from telebot.util import content_type_media

from dff.messengers.telegram import (
    TelegramMessenger,
    TelegramMessage,
    TelegramUI,
    telegram_condition,
)
from dff.messengers.telegram.interface import extract_telegram_request_and_id
from dff.script.core.message import Button
from dff.utils.testing.common import is_interactive_mode

db = dict()  # You can use any other context storage from the library.

bot = TelegramMessenger(os.getenv("TG_BOT_TOKEN", ""))


# %%
script = {
    "root": {
        "start": {
            TRANSITIONS: {
                ("general", "keyboard"): cnd.true(),
            },
        },
        "fallback": {
            RESPONSE: TelegramMessage(text="Finishing test, send /restart command to restart"),
            TRANSITIONS: {
                ("general", "keyboard"): telegram_condition(commands=["start", "restart"])
            },
        },
    },
    "general": {
        "keyboard": {
            RESPONSE: TelegramMessage(
                text="What's 2 + 2?",
                ui=TelegramUI(
                    buttons=[
                        Button(text="4", payload="4"),
                        Button(text="5", payload="5"),
                    ],
                ),
            ),
            TRANSITIONS: {
                ("general", "success"): cnd.exact_match(TelegramMessage(callback_query="4")),
                ("general", "fail"): cnd.exact_match(TelegramMessage(callback_query="5")),
            },
        },
        "success": {
            RESPONSE: TelegramMessage(text="success"),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "fail": {
            RESPONSE: TelegramMessage(text="Incorrect answer, try again"),
            TRANSITIONS: {("general", "keyboard"): cnd.true()},
        },
    },
}


# %%
actor = Actor(script, start_label=("root", "start"), fallback_label=("root", "fallback"))


# %% [markdown]
"""
If you need to work with other types
of queries, you can stack decorators upon the main handler.
"""


# %%
@bot.callback_query_handler(func=lambda call: True)
@bot.message_handler(func=lambda msg: True, content_types=content_type_media)
def handler(update):
    message, ctx_id = extract_telegram_request_and_id(update)

    # retrieve or create a context for the user
    context: Context = db.get(ctx_id, Context(id=ctx_id))
    # add update
    context.add_request(message)

    # apply the actor
    updated_context = actor(context)

    response = updated_context.last_response
    bot.send_response(update.from_user.id, response)
    db[ctx_id] = updated_context  # Save the context.


def main():
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    bot.infinity_polling()


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    main()
