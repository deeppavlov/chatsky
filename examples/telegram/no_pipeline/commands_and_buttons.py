# %% [markdown]
"""
# 2. Commands and Buttons


This module demonstrates how to use the TelegramConnector without the `pipeline` API.

Here, we show how you can integrate command and button reactions into your script.
As in other cases, you only need one handler, as the logic is handled by the actor
and the script.
"""


# %%
import os
from typing import Optional

import dff.core.engine.conditions as cnd
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from telebot import types
from telebot.util import content_type_media

from dff.connectors.messenger.telegram import TELEGRAM_STATE_KEY, TelegramMessenger
from dff.utils.testing.common import set_framework_state

db = dict()
# You can use any other type from `db_connector`.

bot = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %% [markdown]
"""
You can handle various values inside your script.

Use bot.cnd.message_handler to create conditions for message values.
Use bot.cnd.callback_query_handler to create conditions depending on the query values.
The signature of those functions is equivalent to that of the `telebot` methods.

"""


# %%
script = {
    "root": {
        "start": {
            RESPONSE: "",
            TRANSITIONS: {
                ("general", "keyboard"): cnd.true(),
            },
        },
        "fallback": {
            RESPONSE: "Finishing test, send /restart command to restart",
            TRANSITIONS: {
                ("general", "keyboard"): bot.cnd.message_handler(commands=["start", "restart"])
            },
        },
    },
    "general": {
        "keyboard": {
            RESPONSE: {
                "message": "What's 2 + 2?",
                "markup": {
                    0: {"text": "4", "callback_data": "4"},
                    1: {"text": "5", "callback_data": "5"},
                },
            },
            TRANSITIONS: {
                ("general", "success"): bot.cnd.callback_query_handler(
                    func=lambda call: call.data == "4"
                ),
                ("general", "fail"): bot.cnd.callback_query_handler(
                    func=lambda call: call.data == "5"
                ),
            },
        },
        "success": {
            RESPONSE: {"message": "Success!", "markup": None},
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "fail": {
            RESPONSE: {"message": "Incorrect answer, try again", "markup": None},
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

    # add newly received user data to the context
    context = set_framework_state(context, TELEGRAM_STATE_KEY, update, inner_key="data")
    context.add_request(vars(update).get("text", "data"))

    # apply the actor
    context = actor(context)

    # save the context
    db[user_id] = context

    response = context.last_response
    if isinstance(response, str):
        bot.send_message(update.from_user.id, response)
    elif isinstance(response, dict):
        bot.send_message(
            update.from_user.id, response["message"], reply_markup=get_markup(response["markup"])
        )


if __name__ == "__main__":
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    else:
        bot.infinity_polling()
