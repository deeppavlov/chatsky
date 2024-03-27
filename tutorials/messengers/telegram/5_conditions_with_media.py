# %% [markdown]
"""
# Telegram: 5. Conditions with Media

This tutorial shows how to use media-related logic in your script.

Here, %mddoclink(api,messengers.telegram)
message `original_message` component used
for graph navigation according to Telegram events.

Different %mddoclink(api,script.core.message,message)
classes are used for representing different common message features,
like Attachment, Audio, Button, Image, etc.
"""


# %pip install dff[telegram]

# %%
import os

from pydantic import HttpUrl

import dff.script.conditions as cnd
from dff.script import TRANSITIONS, RESPONSE
from dff.script.core.context import Context
from dff.script.core.message import Message, Image
from dff.messengers.telegram import PollingTelegramInterface
from dff.pipeline import Pipeline
from dff.utils.testing.common import is_interactive_mode


# %%

picture_url = HttpUrl(
    "https://avatars.githubusercontent.com/u/29918795?s=200&v=4"
)


# %% [markdown]
"""
To filter user messages depending on whether or not media files were sent,
you can use the `content_types` parameter of the
`Context.last_request.original_message.message.document`.
"""


# %%
interface = PollingTelegramInterface(token=os.environ["TG_BOT_TOKEN"])


def check_if_latest_message_has_photos(ctx: Context, _: Pipeline) -> bool:
    if ctx.last_request is None:
        return False
    if ctx.last_request.original_message is None:
        return False
    if ctx.last_request.original_message.message is None:
        return False
    if ctx.last_request.original_message.message.photo is None:
        return False
    return len(ctx.last_request.original_message.message.photo) > 0


def check_if_latest_message_has_images(ctx: Context, _: Pipeline) -> bool:
    if ctx.last_request is None:
        return False
    if ctx.last_request.original_message is None:
        return False
    if ctx.last_request.original_message.message is None:
        return False
    if ctx.last_request.original_message.message.document is None:
        return False
    return (
        ctx.last_request.original_message.message.document.mime_type
        == "image/jpeg"
    )


def check_if_latest_message_has_text(ctx: Context, _: Pipeline) -> bool:
    if ctx.last_request is None:
        return False
    if ctx.last_request.original_message is None:
        return False
    if ctx.last_request.original_message.message is None:
        return False
    return ctx.last_request.original_message.message.text is None


# %%
script = {
    "root": {
        "start": {
            TRANSITIONS: {
                ("pics", "ask_picture"): cnd.any(
                    [
                        cnd.exact_match(Message(text="/start")),
                        cnd.exact_match(Message(text="/restart")),
                    ]
                )
            },
        },
        "fallback": {
            RESPONSE: Message(
                text="Finishing test, send /restart command to restart"
            ),
            TRANSITIONS: {
                ("pics", "ask_picture"): cnd.any(
                    [
                        cnd.exact_match(Message(text="/start")),
                        cnd.exact_match(Message(text="/restart")),
                    ]
                )
            },
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: Message(text="Send me a picture"),
            TRANSITIONS: {
                ("pics", "send_one"): cnd.any(
                    [
                        # Telegram can put photos
                        # both in 'photo' and 'document' fields.
                        # We should consider both cases
                        # when we check the message for media.
                        check_if_latest_message_has_photos,
                        check_if_latest_message_has_images,
                    ]
                ),
                (
                    "pics",
                    "send_many",
                ): check_if_latest_message_has_text,
                ("pics", "ask_picture"): cnd.true(),
            },
        },
        "send_one": {
            # An HTTP path or a path to a local file can be used here.
            RESPONSE: Message(
                text="Here's my picture!",
                attachments=[Image(source=picture_url)],
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: Message(
                text="Look at my pictures!",
                # An HTTP path or a path to a local file can be used here.
                attachments=list(tuple([Image(source=picture_url)] * 2)),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}


# testing
happy_path = (
    (
        Message(text="/start"),
        Message(text="Send me a picture"),
    ),
    (
        Message(attachments=[Image(source=picture_url)]),
        Message(
            text="Here's my picture!",
            attachments=[Image(source=picture_url)],
        ),
    ),
    (
        Message(text="ok"),
        Message(text="Finishing test, send /restart command to restart"),
    ),
    (
        Message(text="/restart"),
        Message(text="Send me a picture"),
    ),
    (
        Message(text="No"),
        Message(
            text="Look at my pictures!",
            attachments=list(tuple([Image(source=picture_url)] * 2)),
        ),
    ),
    (
        Message(text="ok"),
        Message(text="Finishing test, send /restart command to restart"),
    ),
    (
        Message(text="/restart"),
        Message(text="Send me a picture"),
    ),
)


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=interface,
)


def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
