# %% [markdown]
"""
# 10. No Pipeline Advanced

This example demonstrates how to connect to Telegram without the `pipeline` API.

This shows how you can integrate command and button reactions into your script.
As in other cases, you only need one handler, since the logic is handled by the actor
and the script.
"""


# %%
import os
from typing import Optional

import dff.script.conditions as cnd
from dff.script import Context, Actor, TRANSITIONS, RESPONSE

from telebot import types
from telebot.util import content_type_media

from dff.messengers.telegram import (
    TelegramMessenger,
    TelegramMessage,
    TelegramUI,
    message_handler,
    callback_query_handler,
)
from dff.script.core.message import Button
from dff.utils.testing.common import is_interactive_mode

db = dict()  # You can use any other context storage from the library.

bot = TelegramMessenger(os.getenv("TG_BOT_TOKEN", ""))


# %% [markdown]
"""
You can handle various values inside your script:

* Use `bot.cnd.message_handler` to create conditions for message values.
* Use `bot.cnd.callback_query_handler` to create conditions depending on the query values.

The signature of these functions is equivalent to the signature of the `telebot` methods.
"""


# %%
script = {
    "root": {
        "start": {
            RESPONSE: TelegramMessage(text=""),
            TRANSITIONS: {
                ("general", "keyboard"): cnd.true(),
            },
        },
        "fallback": {
            RESPONSE: TelegramMessage(text="Finishing test, send /restart command to restart"),
            TRANSITIONS: {("general", "keyboard"): message_handler(commands=["start", "restart"])},
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
                ("general", "success"): callback_query_handler(func=lambda call: call.data == "4"),
                ("general", "fail"): callback_query_handler(func=lambda call: call.data == "5"),
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


# %%
def get_markup(data: Optional[dict]):
    if not data:
        return None
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key, item in data.items():
        markup.add(types.InlineKeyboardButton(**item))
    return markup


# %% [markdown]
"""
If you need to work with callback queries or other types
of queries, you can stack decorators upon the main handler.
"""


# %%
@bot.callback_query_handler(func=lambda call: True)
@bot.message_handler(func=lambda msg: True, content_types=content_type_media)
def handler(update):

    # retrieve or create a context for the user
    user_id = (vars(update).get("from_user")).id
    context: Context = db.get(user_id, Context(id=user_id))
    # add update
    context.add_request(TelegramMessage(text=getattr(update, "text", None), update=update))

    # apply the actor
    context = actor(context)

    # save the context
    db[user_id] = context

    response = context.last_response
    bot.send_response(update.from_user.id, response)


def main():
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    bot.infinity_polling()


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    main()
