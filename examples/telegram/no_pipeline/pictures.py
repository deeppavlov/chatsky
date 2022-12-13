"""
Pictures
========

This module demonstrates how to use the TelegramConnector without the `pipeline` API.

Here, we show, how you can receive and send miscellaneous media.
This can be achieved with a single handler function.
"""
# flake8: noqa: E501
import os

from dff.connectors.messenger.telegram.types import TelegramResponse
from dff.core.engine.core.keywords import RESPONSE, TRANSITIONS
from dff.core.engine.core import Context, Actor
from dff.core.engine import conditions as cnd

from telebot import types
from telebot.util import content_type_media

from dff.connectors.messenger.telegram import TELEGRAM_STATE_KEY, TelegramMessenger
from dff.utils.testing.common import set_framework_state

db = dict()
# You can use any other type from `db_connector`.

kitten_id = "Y0WXj3xqJz0"
kitten_ixid = "MnwxMjA3fDB8MXxhbGx8fHx8fHx8fHwxNjY4NjA2NTI0"
kitten_width = 640
kitten_url = f"https://unsplash.com/photos/{kitten_id}/download?ixid={kitten_ixid}&force=true&w={kitten_width}"


def doc_is_photo(message: TelegramResponse):
    return message.document and message.document.mime_type == "image/jpeg"


bot = TelegramMessenger(os.getenv("BOT_TOKEN", "SOMETOKEN"))

"""
Use bot.cnd.message_handler to catch and respond to images.

It can be achieved by passing a function to the `func` parameter or filtering
messages by their `content_type`.
"""

script = {
    "root": {
        "start": {RESPONSE: "", TRANSITIONS: {("pics", "ask_picture"): cnd.true()}},
        "fallback": {
            RESPONSE: "Finishing test, send /restart command to restart",
            TRANSITIONS: {
                ("pics", "ask_picture"): bot.cnd.message_handler(commands=["start", "restart"])
            },
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: "Send me a picture",
            TRANSITIONS: {
                ("pics", "thank", 1.1): cnd.any(
                    [
                        bot.cnd.message_handler(content_types=["photo"]),
                        bot.cnd.message_handler(func=doc_is_photo, content_types=["document"]),
                    ]
                ),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
        "thank": {
            RESPONSE: dict(
                text="Nice! Here is my picture:",
                # An HTTP path or a path to a local file can be used here
                picture=kitten_url,
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "repeat": {
            RESPONSE: "I cannot find the picture. Please, try again.",
            TRANSITIONS: {
                ("pics", "thank", 1.1): cnd.any(
                    [
                        bot.cnd.message_handler(content_types=["photo"]),
                        bot.cnd.message_handler(func=doc_is_photo, content_types=["document"]),
                    ]
                ),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
    },
}

actor = Actor(script, start_label=("root", "start"), fallback_label=("root", "fallback"))

# While most of the time you will be using only one handler to iterate over your script,
# you can always create a separate function that will take care of additional tasks.


def extract_data(message):
    """A function to extract data with"""
    if not message.photo and not message.document:
        return
    photo = message.document or message.photo[-1]
    file = bot.get_file(photo.file_id)
    result = bot.download_file(file.file_path)
    with open("photo.jpg", "wb+") as new_file:
        new_file.write(result)


@bot.message_handler(func=lambda msg: True, content_types=content_type_media)
def handler(update):
    user_id = (vars(update).get("from_user")).id
    context: Context = db.get(user_id, Context(id=user_id))
    context = set_framework_state(context, TELEGRAM_STATE_KEY, update, inner_key="data")
    context.add_request(vars(update).get("text", "data"))

    # Extract data if present
    if isinstance(update, types.Message):
        extract_data(update)

    context = actor(context)

    db[user_id] = context

    response = context.last_response
    if isinstance(response, str):
        bot.send_message(update.from_user.id, response)
    elif isinstance(response, dict):
        bot.send_message(update.from_user.id, response.get("text"))
        with open(response.get("picture"), "rb") as file:
            bot.send_photo(update.from_user.id, file)


if __name__ == "__main__":
    if not os.getenv("BOT_TOKEN"):
        print("`BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    else:
        bot.infinity_polling()
