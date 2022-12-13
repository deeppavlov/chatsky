"""
Pictures
==========

This example shows how to use generic classes from dff.

Here, we show how to process miscellaneous media.
Aside from pictures, you can also send and receive videos, documents, audio files, and locations.
"""
# flake8: noqa: E501
import os

import dff.core.engine.conditions as cnd
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from telebot import types

from dff.connectors.messenger.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
    TELEGRAM_STATE_KEY,
)
from dff.core.pipeline import Pipeline
from dff.connectors.messenger.generics import Response, Image, Attachments
from dff.utils.testing.common import is_interactive_mode, run_interactive_mode

# kitten picture info:
kitten_id = "Y0WXj3xqJz0"
kitten_ixid = "MnwxMjA3fDB8MXxhbGx8fHx8fHx8fHwxNjY4NjA2NTI0"
kitten_width = 640
kitten_url = (
    f"https://unsplash.com/photos/"
    f"{kitten_id}/download?ixid={kitten_ixid}"
    f"&force=true&w={kitten_width}"
)

"""
To detect media, write a function that processes Telebot types, like `Message`.
This function will be passed to `message_handler` in the script.
"""


def doc_is_photo(message: types.Message):
    return message.document and message.document.mime_type == "image/jpeg"


"""
To send media, pass the `Response` class to the `RESPONSE` section of a node.
Both local files and links to media files can be processed.
"""

# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))

script = {
    "root": {
        "start": {RESPONSE: Response(text=""), TRANSITIONS: {("pics", "ask_picture"): cnd.true()}},
        "fallback": {
            RESPONSE: "Finishing test, send /restart command to restart",
            TRANSITIONS: {
                ("pics", "ask_picture"): messenger.cnd.message_handler(
                    commands=["start", "restart"]
                )
            },
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: Response(text="Send me a picture"),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.any(
                    [
                        messenger.cnd.message_handler(content_types=["photo"]),
                        messenger.cnd.message_handler(
                            func=doc_is_photo, content_types=["document"]
                        ),
                    ]
                ),
                ("pics", "send_many", 1.0): messenger.cnd.message_handler(
                    content_types=["sticker"]
                ),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
        "send_one": {
            # An HTTP path or a path to a local file can be used here
            RESPONSE: Response(text="Here's my picture!", image=Image(source=kitten_url)),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: Response(
                text="Look at my pictures",
                # An HTTP path or a path to a local file can be used here
                attachments=Attachments(files=[Image(source=kitten_url)] * 2),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "repeat": {
            RESPONSE: "I cannot find the picture. Please, try again.",
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.any(
                    [
                        messenger.cnd.message_handler(content_types=["photo"]),
                        messenger.cnd.message_handler(
                            func=doc_is_photo, content_types=["document"]
                        ),
                    ]
                ),
                ("pics", "send_many", 1.0): messenger.cnd.message_handler(
                    content_types=["sticker"]
                ),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
    },
}


def extract_data(ctx: Context, actor: Actor):
    """A function to extract data with"""
    message = ctx.framework_states[TELEGRAM_STATE_KEY].get("data")
    if not message or (not message.photo and not doc_is_photo(message)):
        return ctx
    photo = message.document or message.photo[-1]
    file = messenger.get_file(photo.file_id)
    result = messenger.download_file(file.file_path)
    with open("photo.jpg", "wb+") as new_file:
        new_file.write(result)
    return ctx


interface = PollingTelegramInterface(messenger=messenger)

pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    context_storage=dict(),
    messenger_interface=interface,
    pre_services=[extract_data],
)

if __name__ == "__main__":
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    elif is_interactive_mode():
        run_interactive_mode(pipeline)  # run in an interactive shell
    else:
        pipeline.run()  # run in telegram
