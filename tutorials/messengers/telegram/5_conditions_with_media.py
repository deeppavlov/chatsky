# %% [markdown]
"""
# Telegram: 5. Conditions with Media

This tutorial shows how to use media-related logic in your script.
"""

# %pip install dff[telegram]

# %%
import os

from telebot.types import Message

import dff.script.conditions as cnd
from dff.script import Context, TRANSITIONS, RESPONSE
from dff.script.core.message import Image, Attachments
from dff.messengers.telegram import (
    PollingTelegramInterface,
    TelegramMessage,
    telegram_condition,
)
from dff.pipeline import Pipeline
from dff.utils.testing.common import is_interactive_mode


# %%

picture_url = (
    "https://gist.githubusercontent.com/scotthaleen/"
    "32f76a413e0dfd4b4d79c2a534d49c0b/raw"
    "/6c1036b1eca90b341caf06d4056d36f64fc11e88/tiny.jpg"
)


# %% [markdown]
"""
To filter user messages depending on whether or not media files were sent,
you can use the `content_types` parameter of the `telegram_condition`.
"""


# %%
interface = PollingTelegramInterface(token=os.getenv("TG_BOT_TOKEN", ""))


# %%
script = {
    "root": {
        "start": {
            TRANSITIONS: {
                ("pics", "ask_picture"): telegram_condition(commands=["start", "restart"])
            },
        },
        "fallback": {
            RESPONSE: TelegramMessage(text="Finishing test, send /restart command to restart"),
            TRANSITIONS: {
                ("pics", "ask_picture"): telegram_condition(commands=["start", "restart"])
            },
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: TelegramMessage(text="Send me a picture"),
            TRANSITIONS: {
                ("pics", "send_one"): cnd.any(
                    [
                        # Telegram can put photos both in 'photo' and 'document' fields.
                        # We should consider both cases when we check the message for media.
                        telegram_condition(content_types=["photo"]),
                        telegram_condition(
                            func=lambda message: (
                                # check attachments in message properties
                                message.document
                                and message.document.mime_type == "image/jpeg"
                            ),
                            content_types=["document"],
                        ),
                    ]
                ),
                ("pics", "send_many"): telegram_condition(content_types=["text"]),
                ("pics", "ask_picture"): cnd.true(),
            },
        },
        "send_one": {
            # An HTTP path or a path to a local file can be used here.
            RESPONSE: TelegramMessage(
                text="Here's my picture!",
                attachments=Attachments(files=[Image(source=picture_url)]),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: TelegramMessage(
                text="Look at my pictures!",
                # An HTTP path or a path to a local file can be used here.
                attachments=Attachments(files=[Image(source=picture_url)] * 2),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}


# testing
happy_path = (
    (TelegramMessage(text="/start"), TelegramMessage(text="Send me a picture")),
    (
        TelegramMessage(attachments=Attachments(files=[Image(source=picture_url)])),
        TelegramMessage(
            text="Here's my picture!",
            attachments=Attachments(files=[Image(source=picture_url)]),
        ),
    ),
    (
        TelegramMessage(text="ok"),
        TelegramMessage(text="Finishing test, send /restart command to restart"),
    ),
    (TelegramMessage(text="/restart"), TelegramMessage(text="Send me a picture")),
    (
        TelegramMessage(text="No"),
        TelegramMessage(
            text="Look at my pictures!",
            attachments=Attachments(files=[Image(source=picture_url)] * 2),
        ),
    ),
    (
        TelegramMessage(text="ok"),
        TelegramMessage(text="Finishing test, send /restart command to restart"),
    ),
    (TelegramMessage(text="/restart"), TelegramMessage(text="Send me a picture")),
)


# %%
def extract_data(ctx: Context, _: Pipeline):  # A function to extract data with
    message = ctx.last_request
    if message is None:
        return ctx
    update = getattr(message, "update", None)
    if update is None:
        return ctx
    if not isinstance(update, Message):
        return ctx
    if (
        # check attachments in update properties
        not update.photo
        and not (update.document and update.document.mime_type == "image/jpeg")
    ):
        return ctx
    photo = update.document or update.photo[-1]
    file = interface.messenger.get_file(photo.file_id)
    result = interface.messenger.download_file(file.file_path)
    with open("photo.jpg", "wb+") as new_file:
        new_file.write(result)
    return ctx


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=interface,
    pre_services=[extract_data],
)


def main():
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    main()
