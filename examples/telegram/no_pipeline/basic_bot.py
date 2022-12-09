"""
Basic Bot
==========

This module demonstrates how to use the TelegramConnector without the `pipeline` API.

This approach remains much closer to the usual workflow of pytelegrambotapi developers.
You create a 'bot' (TelegramMessenger) and define handlers that react to messages.
The conversation logic is in your script, so you only need one handler most of the time.
Go for it, if you need a quick prototype or have no interest in using the `pipeline` API.

Here, we deploy a basic bot that only reacts to messages. For other message types and triggers
see the other examples.
"""
import os
import sys

import dff.core.engine.conditions as cnd
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from telebot.util import content_type_media

from dff.connectors.messenger.telegram import TELEGRAM_STATE_KEY, TelegramMessenger
from dff.utils.testing.common import check_env_var, set_framework_state

db = dict()
# You can use any other type from `db_connector`.

bot = TelegramMessenger(os.getenv("BOT_TOKEN", "SOMETOKEN"))

"""
Here, we use a standard script without any Telegram-specific conversation logic.
This is enough to get a bot up and running.
"""

script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
        "node1": {
            RESPONSE: "Hi, how are you?",
            TRANSITIONS: {"node2": cnd.regexp(r".*(good|fine|great).*")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": cnd.regexp(r"(music[.!]{0,1}|.*about music[.!]{0,1})")},
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")},
        },
        "node4": {RESPONSE: "bye", TRANSITIONS: {"node1": cnd.regexp(r".*(restart|start|start again).*")}},
        "fallback_node": {
            RESPONSE: "Ooops",
            TRANSITIONS: {"node1": cnd.true()},
        },
    }
}

actor = Actor(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))


# The content_type parameter is set to the `content_type_media` constant,
# so that the bot can reply to images, stickers, etc.
@bot.message_handler(func=lambda message: True, content_types=content_type_media)
def dialog_handler(update):
    """
    | Standard handler that replies with `Actor` responses.

    | If you need to need to process other updates in addition to messages,
    | just stack the corresponding handler decorators on top of the function.

    update: Any Telegram update. What types you process depends on the decorators you stack upon the handler.
    """
    # retrieve or create a context for the user
    user_id = (vars(update).get("from_user")).id
    context: Context = db.get(user_id, Context(id=user_id))
    # add newly received user data to the context
    context = set_framework_state(context, TELEGRAM_STATE_KEY, update, inner_key="data")
    # this step is required for cnd.%_handler conditions to work
    context.add_request(vars(update).get("text", "data"))

    # apply the actor
    updated_context = actor(context)

    response = updated_context.last_response
    if isinstance(response, str):
        bot.send_message(update.from_user.id, response)
    # optionally provide conditions to use other response methods
    # elif isinstance(response, bytes):
    #     messenger.send_document(update.from_user.id, response)

    # save the context
    db[user_id] = updated_context


if __name__ == "__main__":
    check_env_var("BOT_TOKEN")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Stopping bot")
        sys.exit(0)
