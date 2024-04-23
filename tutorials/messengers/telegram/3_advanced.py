# %% [markdown]
"""
# Telegram: 3. Advanced

The following tutorial shows how to run a regular DFF script in Telegram.
It asks users for the '/start' command and then loops in one place.

Here, %mddoclink(api,messengers.telegram,PollingTelegramInterface)
class and [telebot](https://pytba.readthedocs.io/en/latest/index.html)
library are used for accessing telegram API in polling mode.

Telegram API token is required to access telegram API.
"""

# %pip install dff[telegram]

# %%
import asyncio
import os

from pydantic import HttpUrl
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from dff.script import conditions as cnd
from dff.script import RESPONSE, TRANSITIONS, Message
from dff.messengers.telegram import PollingTelegramInterface
from dff.pipeline import Pipeline
from dff.script.core.keywords import GLOBAL
from dff.script.core.message import Document, Image, Location, Sticker
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
In order to integrate your script with Telegram, you need an instance of
`TelegramMessenger` class and one of the following interfaces:
`PollingMessengerInterface` or `WebhookMessengerInterface`.

`TelegramMessenger` encapsulates the bot logic. Like Telebot,
`TelegramMessenger` only requires a token to run. However, all parameters
from the Telebot class can be passed as keyword arguments.

The two interfaces connect the bot to Telegram. They can be passed directly
to the DFF `Pipeline` instance.
"""

#%%

image_url = HttpUrl("https://avatars.githubusercontent.com/u/29918795?s=200&v=4")

formatted_text = r"""
Here's your formatted text\!  
You can see **text in bold** and _text in italic_\.  
\> Here's a [link](https://github.com/deeppavlov/dialog_flow_framework) in a quote\.  
Run /start command again to restart\.
"""

location_data = {"latitude": 59.9386, "longitude": 30.3141}

sticker_data = {
    "id": "CAACAgIAAxkBAAErBZ1mKAbZvEOmhscojaIL5q0u8vgp1wACRygAAiSjCUtLa7RHZy76ezQE",
}

image_data = {
    "source": image_url,
    "title": "DeepPavlov logo",
    "has_spoiler": True,
    "filename": "deeppavlov_logo.png",
}

document_thumbnail = asyncio.run(Image(source=image_url).get_bytes(None))

document_data = {
    "source": HttpUrl("https://aclanthology.org/P18-4021.pdf"),
    "title": "DeepPavlov article",
    "filename": "deeppavlov_article.pdf",
    "thumbnail": document_thumbnail,
}


# %%
script = {
    GLOBAL: {
        TRANSITIONS: {
            ("main_flow", "hmmm_node"): cnd.exact_match(Message("/start")),
        }
    },
    "main_flow": {
        "start_node": {},
        "hmmm_node": {
            RESPONSE: Message(
                attachments=[
                    Location(
                        latitude=58.431610,
                        longitude=27.792887,
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton("Cute formatted text!", callback_data="formatted"),
                                ],
                                [
                                    InlineKeyboardButton("Multiple attachments!", callback_data="attachments"),
                                ],
                                [
                                    InlineKeyboardButton("Secret image!", callback_data="secret"),
                                ],
                                [
                                    InlineKeyboardButton("Document with thumbnail!", callback_data="thumbnail"),
                                ],
                                [
                                    InlineKeyboardButton("Restart!", callback_data="restart"),
                                    InlineKeyboardButton("Quit!", callback_data="quit"),
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
                "hmmm_node": cnd.has_callback_query("restart"),
                "fallback_node": cnd.has_callback_query("quit"),
            }
        },
        "formatted_node": {
            RESPONSE: Message(formatted_text, parse_mode=ParseMode.MARKDOWN_V2),
        },
        "attachments_node": {
            RESPONSE: Message(
                "Here's your message with multiple attachments (a location and a sticker)!\nRun /start command again to restart.",
                attachments=[
                    Location(**location_data),
                    Sticker(**sticker_data),
                ],
            ),
        },
        "secret_node": {
            RESPONSE: Message(
                "Here's your secret image! Run /start command again to restart.",
                attachments=[Image(**image_data)],
            ),
        },
        "thumbnail_node": {
            RESPONSE: Message(
                "Here's your document with tumbnail! Run /start command again to restart.",
                attachments=[Document(**document_data)],
            ),
        },
        "fallback_node": {
            RESPONSE: Message("Bot has entered unrecoverable state :/\nRun /start command again to restart."),
        },
    }
}

# this variable is only for testing
happy_path = (
    (Message("/start"), Message("Hi")),
    (Message("Hi"), Message("Hi")),
    (Message("Bye"), Message("Hi")),
)


# %%
interface = PollingTelegramInterface(token=os.environ["TG_BOT_TOKEN"])


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("main_flow", "start_node"),
    fallback_label=("main_flow", "fallback_node"),
    messenger_interface=interface,
    # The interface can be passed as a pipeline argument.
)


def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
