#!/usr/bin/env python3
"""
This module demonstrates how to use the TelegramConnector without the dff.core.runner add-on.
This approach remains much closer to the usual workflow of pytelegrambotapi developers, so go for it
if you need a quick prototype or have no interest in using the dff.core.runner.
"""
import os
import sys

from dff.core.engine.core.keywords import RESPONSE, TRANSITIONS
from dff.core.engine.core import Context, Actor
from dff.core.engine import conditions as cnd

from telebot import types
from telebot.util import content_type_media

from dff.connectors.messenger.telegram.connector import TelegramConnector
from dff.connectors.messenger.telegram.utils import set_state, get_user_id, get_initial_context


db = dict()
# Optionally, you can use database connection implementations from the dff ecosystem.
# from df_db_connector import SqlConnector
# db = SqlConnector("SOME_URI")


def doc_is_photo(message):
    return message.document and message.document.mime_type == "image/jpeg"


bot = TelegramConnector(os.getenv("BOT_TOKEN", "SOMETOKEN"))

script = {
    "root": {
        "start": {RESPONSE: "", TRANSITIONS: {("pics", "ask_picture"): cnd.true()}},
        "fallback": {
            RESPONSE: "Finishing test, send /restart command to restart",
            TRANSITIONS: {("pics", "ask_picture"): bot.cnd.message_handler(commands=["start", "restart"])},
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
                picture=os.path.join(os.path.dirname(os.path.realpath(__file__)), "kitten.jpg"),
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
    user_id = get_user_id(update)
    context: Context = db.get(user_id, get_initial_context(user_id))
    context = set_state(context, update)

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
    if "BOT_TOKEN" not in os.environ:
        print("BOT_TOKEN variable needs to be set to continue")
        sys.exit(1)

    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("Stopping bot")
        sys.exit(0)
