"""
This module demonstrates how to use the TelegramConnector without the dff.core.runner add-on.
This approach remains much closer to the usual workflow of pytelegrambotapi developers, so go for it
if you need a quick prototype or have no interest in using the dff.core.runner.
"""
import os
import sys

import dff.core.engine.conditions as cnd
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from telebot.util import content_type_media

from dff.connectors.messenger.telegram.connector import TelegramConnector
from dff.connectors.messenger.telegram.utils import set_state, get_user_id, get_initial_context
from examples.telegram._telegram_utils import check_env_bot_tokens

db = dict()
# Optionally, you can use database connection implementations from the dff ecosystem.
# from df_db_connector import SqlConnector
# db = SqlConnector("SOME_URI")

bot = TelegramConnector(os.getenv("BOT_TOKEN", "SOMETOKEN"))

script = {
    "greeting_flow": {
        "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},  # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: "Hi, how are you?",  # When the agent goes to node1, we return "Hi, how are you?"
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
        "fallback_node": {  # We get to this node if an error occurred while the agent was running
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
    | Standard handler that replies with dff.core.engine's :py:class:`~dff.core.engine.core.Actor` responses.

    | Since the logic of processing Telegram updates
    | will be wholly handled by the :py:class:`~dff.core.engine.core.Actor`,
    | only one handler is sufficient to run the bot.
    | If you need to need to process other updates in addition to messages,
    | just stack the corresponding handler decorators on top of the function.

    Parameters
    -----------

    update: :py:class:`~telebot.types.JsonDeserializeable`
        Any Telegram update. What types you process depends on the decorators you stack upon the handler.

    """
    # retrieve or create a context for the user
    user_id = get_user_id(update)
    context: Context = db.get(user_id, get_initial_context(user_id))
    # add newly received user data to the context
    context = set_state(context, update)  # this step is required for cnd.%_handler conditions to work

    # apply the actor
    updated_context = actor(context)

    response = updated_context.last_response
    if isinstance(response, str):
        bot.send_message(update.from_user.id, response)
    # optionally provide conditions to use other response methods
    # elif isinstance(response, bytes):
    #     bot.send_document(update.from_user.id, response)

    # save the context
    db[user_id] = updated_context


if __name__ == "__main__":
    check_env_bot_tokens()
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Stopping bot")
        sys.exit(0)
