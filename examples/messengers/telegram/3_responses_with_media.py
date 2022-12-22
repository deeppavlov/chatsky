# %% [markdown]
"""
# 3. Responses with Media

This example demonstrates how to configure your bot to exchange media
using the generic `Response` class from DFF.
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
from dff.script.responses.generics import Response, Image
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
To detect media, write a function that processes Telebot types, like `Message`.
This function will be passed to `message_handler` in the script.
"""


# %%
def doc_is_photo(message: types.Message):
    return message.document and message.document.mime_type == "image/jpeg"


# %% [markdown]
"""
To send media, instantiate the generic `Response` class with the property `image`
set to `Image` class. For the latter, you can use both online media files and
local media files on your computer. The same applies to audio, video, documents and
other types of media.
"""


# %%
# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
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
                ("pics", "send_one", 1.1): cnd.true(),
            },
        },
        "send_one": {
            # An HTTP path or a path to a local file can be used here.
            RESPONSE: Response(text="Here's my picture!", image=Image(source=kitten_url)),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "repeat": {
            RESPONSE: "I cannot find the picture. Please, try again.",
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.true(),
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
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # run in an interactive shell
    else:
        if not os.getenv("TG_BOT_TOKEN"):
            print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
        pipeline.run()
