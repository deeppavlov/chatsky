# %% [markdown]
"""
# Telegram: 3. Advanced

The following tutorial shows several advanced cases of user-to-bot interaction.

Here, %mddoclink(api,messengers.telegram.interface,LongpollingInterface)
class and [python-telegram-bot](https://docs.python-telegram-bot.org/)
library are used for accessing telegram API in polling mode.

Telegram API token is required to access telegram API.
"""

# %pip install chatsky[telegram]

# %%
import os
from hashlib import sha256
from urllib.request import urlopen

from pydantic import HttpUrl
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from chatsky.script import conditions as cnd
from chatsky.script import RESPONSE, TRANSITIONS, Message
from chatsky.messengers.telegram import LongpollingInterface
from chatsky.pipeline import Pipeline
from chatsky.script.core.context import Context
from chatsky.script.core.keywords import GLOBAL
from chatsky.script.core.message import (
    DataAttachment,
    Document,
    Image,
    Location,
    Sticker,
)
from chatsky.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
This bot shows different special telegram messenger interface use cases,
such as:

1. Interactive keyboard with buttons.
2. Text formatted with Markdown V2.
3. Multiple attachments of different kind handling.
4. Image with a spoiler.
5. Document with a thumbnail.
6. Attachment bytes hash.

Check out
[this](https://docs.python-telegram-bot.org/en/latest/telegram.bot.html#telegram.Bot)
class for information about different arguments
for sending attachments, `send_...` methods.

Last option ("Raw attachments!") button might be especially interesting,
because it shows how bot percepts different telegram attachments sent by user
in terms and datastructures of Chatsky.
"""

# %%

EXAMPLE_ATTACHMENT_SOURCE = (
    "https://github.com/deeppavlov/chatsky/wiki/example_attachments"
)

image_url = HttpUrl(f"{EXAMPLE_ATTACHMENT_SOURCE}/deeppavlov.png")

formatted_text = """
Visit [this link](https://core.telegram.org/bots/api#formatting-options)
for more information about formatting options in telegram\.

Run /start command again to restart\.
"""  # noqa: W605

location_data = {"latitude": 59.9386, "longitude": 30.3141}

sticker_data = {
    "id": (
        "CAACAgIAAxkBAAErBZ1mKAbZvEOmhscojaIL5q0u8v"
        + "gp1wACRygAAiSjCUtLa7RHZy76ezQE"
    ),
}

image_data = {
    "source": image_url,
    "caption": "DeepPavlov logo",
    "has_spoiler": True,
    "filename": "deeppavlov_logo.png",
}

document_data = {
    "source": HttpUrl(f"{EXAMPLE_ATTACHMENT_SOURCE}/deeppavlov-article.pdf"),
    "caption": "DeepPavlov article",
    "filename": "deeppavlov_article.pdf",
    "thumbnail": urlopen(str(image_url)).read(),
}


# %%
async def hash_data_attachment_request(ctx: Context, pipe: Pipeline) -> Message:
    attachment = [
        a for a in ctx.last_request.attachments if isinstance(a, DataAttachment)
    ]
    if len(attachment) > 0:
        attachment_bytes = await attachment[0].get_bytes(
            pipe.messenger_interface
        )
        attachment_hash = sha256(attachment_bytes).hexdigest()
        resp_format = (
            "Here's your previous request first attachment sha256 hash: `{}`!\n"
            + "Run /start command again to restart."
        )
        return Message(
            resp_format.format(
                attachment_hash, parse_mode=ParseMode.MARKDOWN_V2
            )
        )
    else:
        return Message(
            "Last request did not contain any data attachment!\n"
            + "Run /start command again to restart."
        )


# %%
script = {
    GLOBAL: {
        TRANSITIONS: {
            ("main_flow", "main_node"): cnd.exact_match("/start"),
        }
    },
    "main_flow": {
        "start_node": {},
        "main_node": {
            RESPONSE: Message(
                attachments=[
                    Location(
                        latitude=58.431610,
                        longitude=27.792887,
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "Cute formatted text!",
                                        callback_data="formatted",
                                    ),
                                ],
                                [
                                    InlineKeyboardButton(
                                        "Multiple attachments!",
                                        callback_data="attachments",
                                    ),
                                ],
                                [
                                    InlineKeyboardButton(
                                        "Secret image!", callback_data="secret"
                                    ),
                                ],
                                [
                                    InlineKeyboardButton(
                                        "Document with thumbnail!",
                                        callback_data="thumbnail",
                                    ),
                                ],
                                [
                                    InlineKeyboardButton(
                                        "First attachment bytes hash!",
                                        callback_data="hash",
                                    ),
                                ],
                                [
                                    InlineKeyboardButton(
                                        "Restart!", callback_data="restart"
                                    ),
                                    InlineKeyboardButton(
                                        "Quit!", callback_data="quit"
                                    ),
                                ],
                            ],
                        ),
                    ),
                ],
            ),
            TRANSITIONS: {
                "formatted_node": cnd.has_callback_query("formatted"),
                "attachments_node": cnd.has_callback_query("attachments"),
                "secret_node": cnd.has_callback_query("secret"),
                "thumbnail_node": cnd.has_callback_query("thumbnail"),
                "hash_init_node": cnd.has_callback_query("hash"),
                "main_node": cnd.has_callback_query("restart"),
                "fallback_node": cnd.has_callback_query("quit"),
            },
        },
        "formatted_node": {
            RESPONSE: Message(formatted_text, parse_mode=ParseMode.MARKDOWN_V2),
        },
        "attachments_node": {
            RESPONSE: Message(
                "Here's your message with multiple attachments "
                + "(a location and a sticker)!\n"
                + "Run /start command again to restart.",
                attachments=[
                    Location(**location_data),
                    Sticker(**sticker_data),
                ],
            ),
        },
        "secret_node": {
            RESPONSE: Message(
                "Here's your secret image! "
                + "Run /start command again to restart.",
                attachments=[Image(**image_data)],
            ),
        },
        "thumbnail_node": {
            RESPONSE: Message(
                "Here's your document with tumbnail! "
                + "Run /start command again to restart.",
                attachments=[Document(**document_data)],
            ),
        },
        "hash_init_node": {
            RESPONSE: Message(
                "Alright! Now send me a message with data attachment "
                + "(audio, video, animation, image, sticker or document)!"
            ),
            TRANSITIONS: {"hash_request_node": cnd.true()},
        },
        "hash_request_node": {
            RESPONSE: hash_data_attachment_request,
        },
        "fallback_node": {
            RESPONSE: Message(
                "Bot has entered unrecoverable state:"
                + "/\nRun /start command again to restart."
            ),
        },
    },
}


# %%
interface = LongpollingInterface(token=os.environ["TG_BOT_TOKEN"])


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("main_flow", "start_node"),
    fallback_label=("main_flow", "fallback_node"),
    messenger_interface=interface,
    # The interface can be passed as a pipeline argument.
)


if __name__ == "__main__":
    if is_interactive_mode():
        # prevent run during doc building
        pipeline.run()
