#!/usr/bin/env python3
"""
The replies below use generic classes.
Using generic responses, you can use send local files as well as links to external ones.
"""
import os
import sys

import dff.core.engine.conditions as cnd
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from telebot import types

from dff.connectors.messenger.telegram.connector import TelegramConnector
from dff.connectors.messenger.telegram.request_provider import PollingRequestProvider

from dff.core.runner import ScriptRunner

from dff.connectors.messenger.generics import Response, Image, Attachments


def doc_is_photo(message: types.Message):
    return message.document and message.document.mime_type == "image/jpeg"


my_image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "kitten.jpg")

bot = TelegramConnector(os.getenv("BOT_TOKEN", "SOMETOKEN"))

script = {
    "root": {
        "start": {RESPONSE: Response(text=""), TRANSITIONS: {("pics", "ask_picture"): cnd.true()}},
        "fallback": {
            RESPONSE: "Finishing test, send /restart command to restart",
            TRANSITIONS: {("pics", "ask_picture"): bot.cnd.message_handler(commands=["start", "restart"])},
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: Response(text="Send me a picture"),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.any(
                    [
                        bot.cnd.message_handler(content_types=["photo"]),
                        bot.cnd.message_handler(func=doc_is_photo, content_types=["document"]),
                    ]
                ),
                ("pics", "send_many", 1.0): bot.cnd.message_handler(content_types=["sticker"]),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
        "send_one": {
            RESPONSE: Response(text="Here's my picture!", image=Image(source=my_image_path)),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: Response(
                text="Look at my pictures",
                attachments=Attachments(files=[Image(source=my_image_path)] * 2),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "repeat": {
            RESPONSE: "I cannot find the picture. Please, try again.",
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.any(
                    [
                        bot.cnd.message_handler(content_types=["photo"]),
                        bot.cnd.message_handler(func=doc_is_photo, content_types=["document"]),
                    ]
                ),
                ("pics", "send_many", 1.0): bot.cnd.message_handler(content_types=["sticker"]),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
    },
}


def extract_data(ctx: Context, actor: Actor):
    """A function to extract data with"""
    message = ctx.framework_states["TELEGRAM_CONNECTOR"].get("data")
    if not message or (not message.photo and not doc_is_photo(message)):
        return ctx
    photo = message.document or message.photo[-1]
    file = bot.get_file(photo.file_id)
    result = bot.download_file(file.file_path)
    with open("photo.jpg", "wb+") as new_file:
        new_file.write(result)
    return ctx


provider = PollingRequestProvider(bot=bot)

runner = ScriptRunner(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    db=dict(),
    request_provider=provider,
    pre_annotators=[extract_data],
)

if __name__ == "__main__":
    if "BOT_TOKEN" not in os.environ:
        print("BOT_TOKEN variable needs to be set to continue")
        sys.exit(1)

    runner.start()
