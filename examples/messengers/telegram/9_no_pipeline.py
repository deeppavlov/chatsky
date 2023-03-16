# %% [markdown]
"""
# 9. No Pipeline

This example shows how to connect to Telegram without the `pipeline` API.

This approach is much closer to the usual pytelegrambotapi developer workflow.
You create a 'bot' (TelegramMessenger) and define handlers that react to messages.
The conversation logic is in your script, so in most cases you only need one handler.
Use it if you need a quick prototype or aren't interested in using the `pipeline` API.

Here, we deploy a basic bot that reacts only to messages.
"""


# %%
import os

from dff.script import Context, Actor
from telebot.util import content_type_media
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH
from dff.messengers.telegram import TelegramMessenger
from dff.messengers.telegram.interface import extract_telegram_request_and_id
from dff.utils.testing.common import is_interactive_mode

db = dict()  # You can use any other context storage from the library.

bot = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %% [markdown]
"""
Here we use a standard script without any Telegram-specific conversation logic.
This is enough to get a bot up and running.
"""


# %%
actor = Actor(
    TOY_SCRIPT,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

happy_path = HAPPY_PATH


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
