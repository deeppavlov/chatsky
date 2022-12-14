# %% [markdown]
"""
# 11. No Pipeline

This example shows how to use the TelegramConnector without the `pipeline` API.

This approach is much closer to the usual pytelegrambotapi developer workflow.
You create a 'bot' (TelegramMessenger) and define handlers that react to messages.
The conversation logic is in your script, so in most cases you only need one handler.
Use it if you need a quick prototype or aren't interested in using the `pipeline` API.

Here, we deploy a basic bot that reacts only to messages.
"""


# %%
import os

import dff.core.engine.conditions as cnd
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from telebot.util import content_type_media

from dff.connectors.messenger.telegram import TELEGRAM_STATE_KEY, TelegramMessenger
from dff.utils.testing.common import set_framework_state

db = dict()  # You can use any other type from `db_connector`.

bot = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %% [markdown]
"""
Here we use a standard script without any Telegram-specific conversation logic.
This is enough to get a bot up and running.
"""


# %%
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
        "node4": {
            RESPONSE: "bye",
            TRANSITIONS: {"node1": cnd.regexp(r".*(restart|start|start again).*")},
        },
        "fallback_node": {
            RESPONSE: "Ooops",
            TRANSITIONS: {"node1": cnd.true()},
        },
    }
}


# %%
actor = Actor(
    script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


# %% [markdown]
"""
Standard handler that replies with `Actor` responses.
If you need to process other updates in addition to messages,
just stack the corresponding handler decorators on top of the function.

The `content_type` parameter is set to the `content_type_media` constant,
so that the bot can reply to images, stickers, etc.
"""


# %%
@bot.message_handler(func=lambda message: True, content_types=content_type_media)
def dialog_handler(update):

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
    # Optionally provide conditions to use other response methods.
    # elif isinstance(response, bytes):
    #     messenger.send_document(update.from_user.id, response)

    db[user_id] = updated_context  # Save the context.


if __name__ == "__main__":
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    else:
        bot.infinity_polling()
