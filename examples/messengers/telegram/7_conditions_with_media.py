# %% [markdown]
"""
# 7. Conditions with Media

This example shows how to use media-related logic in your script.
"""

# %%
import os

import dff.script.conditions as cnd
from dff.script import Context, Actor, TRANSITIONS, RESPONSE

from telebot import types

from dff.messengers.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
)
from dff.pipeline import Pipeline
from dff.script.responses.generics import Response, Image, Attachments
from dff.utils.testing.common import is_interactive_mode, run_interactive_mode


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
def doc_is_photo(message: types.Message):
    return message.document and message.document.mime_type == "image/jpeg"


# %%
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %%
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
            # An HTTP path or a path to a local file can be used here.
            RESPONSE: Response(text="Here's my picture!", image=Image(source=kitten_url)),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: Response(
                text="Look at my pictures",
                # An HTTP path or a path to a local file can be used here.
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


# %%
def extract_data(ctx: Context, actor: Actor):  # A function to extract data with
    message = ctx.last_request
    if not message or (not message.photo and not doc_is_photo(message)):
        return ctx
    photo = message.document or message.photo[-1]
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
