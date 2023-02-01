# %% [markdown]
"""
# 5. Conditions with Media

This example shows how to use media-related logic in your script.
"""

# %%
import os

from telebot.types import Message

import dff.script.conditions as cnd
from dff.script import Context, Actor, TRANSITIONS, RESPONSE

from dff.messengers.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
    TelegramMessage,
    Image,
    Attachments,
    message_handler,
)
from dff.pipeline import Pipeline
from dff.utils.testing.common import is_interactive_mode


# %%
# kitten picture info:
kitten_id = "Y0WXj3xqJz0"
kitten_ixid = "MnwxMjA3fDB8MXxhbGx8fHx8fHx8fHwxNjY4NjA2NTI0"
kitten_width = 640
kitten_url = (
    f"https://unsplash.com/photos/"
    f"{kitten_id}/download?ixid={kitten_ixid}"
    f"&force=true&w={kitten_width}"
)

picture_url = "https://folklore.linghub.ru/api/gallery/300/23.JPG"


# %% [markdown]
"""
To filter user messages depending on whether or not media files were sent,
you can use the `content_types` parameter of the `message_handler`.

If you want to access properties of some specific file, you can get
the message from the context:

.. code-block:: python

    message = ctx.last_request

The files will then be accessible as properties: message.photo, etc.

"""


# %%
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %%
script = {
    "root": {
        "start": {
            RESPONSE: TelegramMessage(text=""),
            TRANSITIONS: {("pics", "ask_picture"): message_handler(commands=["start", "restart"])},
        },
        "fallback": {
            RESPONSE: TelegramMessage(text="Finishing test, send /restart command to restart"),
            TRANSITIONS: {("pics", "ask_picture"): message_handler(commands=["start", "restart"])},
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
                        message_handler(content_types=["photo"]),
                        message_handler(
                            func=lambda message: (
                                # check attachments in message properties
                                message.document
                                and message.document.mime_type == "image/jpeg"
                            ),
                            content_types=["document"],
                        ),
                    ]
                ),
                ("pics", "send_many"): message_handler(content_types=["text"]),
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
        TelegramMessage(attachments=Attachments(files=[Image(source=kitten_url)])),
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
def extract_data(ctx: Context, actor: Actor):  # A function to extract data with
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
    file = messenger.get_file(photo.file_id)
    result = messenger.download_file(file.file_path)
    with open("photo.jpg", "wb+") as new_file:
        new_file.write(result)
    return ctx


# %%
interface = PollingTelegramInterface(messenger=messenger)


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=interface,
    pre_services=[extract_data],
)


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    pipeline.run()
