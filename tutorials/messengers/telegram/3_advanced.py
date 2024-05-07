# %% [markdown]
"""
# Telegram: 3. Advanced

The following tutorial shows several advanced cases of user-to-bot interaction.

Here, %mddoclink(api,messengers.telegram.interface,PollingTelegramInterface)
class and [python-telegram-bot](https://docs.python-telegram-bot.org/)
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
from dff.script.core.context import Context
from dff.script.core.keywords import GLOBAL
from dff.script.core.message import Document, Image, Location, Sticker
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
This bot shows different special telegram messenger interface use cases,
such as:

1. Interactive keyboard with buttons.
2. Text formatted with Markdown V2.
3. Multiple attachments of different kind handling.
4. Image with a spoiler.
5. Document with a thumbnail.
6. Raw representation of different data user can send to the bot.

Last option ("Raw attachments!") button might be especially interesting,
because it shows how bot precepts different telegram attachments sent by user
in terms and datastructures of Dialog Flow Framework.
"""

#%%

image_url = HttpUrl("https://cdn.jsdelivr.net/gh/deeppavlov/dialog_flow_framework@example-attachments/deeppavlov.png")

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
    "source": HttpUrl("https://cdn.jsdelivr.net/gh/deeppavlov/dialog_flow_framework@example-attachments/deeppavlov-article.pdf"),
    "title": "DeepPavlov article",
    "filename": "deeppavlov_article.pdf",
    "thumbnail": document_thumbnail,
}


# %%
formatted_request = r"""
Here's your previous request\!
```json
{}
```
Run /start command again to restart\.
"""

def stringify_previous_request(ctx: Context, _: Pipeline) -> Message:
    dump = ctx.last_request.model_dump_json(indent=4)
    return Message(formatted_request.format(dump), parse_mode=ParseMode.MARKDOWN_V2)


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
                                    InlineKeyboardButton("Raw attachments!", callback_data="raw"),
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
                "raw_init_node": cnd.has_callback_query("raw"),
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
        "raw_init_node": {
            RESPONSE: Message("Alright! Now send me any message and I'll send you it's raw data!"),
            TRANSITIONS: { "raw_request_node": cnd.true },
        },
        "raw_request_node": {
            RESPONSE: stringify_previous_request,
        },
        "fallback_node": {
            RESPONSE: Message("Bot has entered unrecoverable state :/\nRun /start command again to restart."),
        },
    }
}


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
