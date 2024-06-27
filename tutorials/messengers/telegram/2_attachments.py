# %% [markdown]
"""
# Telegram: 2. Attachments

The following tutorial shows how to send different attachments using
telegram interfaces.

Here, %mddoclink(api,messengers.telegram.interface,LongpollingInterface)
class and [python-telegram-bot](https://docs.python-telegram-bot.org/)
library are used for accessing telegram API in polling mode.

Telegram API token is required to access telegram API.
"""

# %pip install dff[telegram]

# %%
import os

from pydantic import HttpUrl

from dff.script import conditions as cnd
from dff.script import GLOBAL, RESPONSE, TRANSITIONS, Message
from dff.messengers.telegram import LongpollingInterface
from dff.pipeline import Pipeline
from dff.script.core.message import (
    Animation,
    Audio,
    Contact,
    Document,
    Location,
    Image,
    MediaGroup,
    Poll,
    PollOption,
    Sticker,
    Video,
    VideoMessage,
    VoiceMessage,
)
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
Example attachment data is specified below in form of dictionaries.
List of attachments that telegram messenger interface can send can
be found here:
%mddoclink(api,messengers.telegram.abstract,_AbstractTelegramInterface.supported_request_attachment_types).
"""

# %%

EXAMPLE_ATTACHMENT_SOURCE = (
    "https://github.com/deeppavlov/"
    + "dialog_flow_framework/wiki/example_attachments"
)

location_data = {"latitude": 50.65, "longitude": 3.916667}

contact_data = {
    "phone_number": "8-900-555-35-35",
    "first_name": "Hope",
    "last_name": "Credit",
}

sticker_data = {
    "id": (
        "CAACAgIAAxkBAAErAAFXZibO5ksphCKS"
        + "XSe1CYiw5588yqsAAkEAAzyKVxogmx2BPCogYDQE"
    ),
    "title": "A sticker I've just found",
}

audio_data = {
    "source": HttpUrl(
        f"{EXAMPLE_ATTACHMENT_SOURCE}/separation-william-king.mp3"
    ),
    "title": "Separation melody by William King",
}

video_data = {
    "source": HttpUrl(
        f"{EXAMPLE_ATTACHMENT_SOURCE}/crownfall-lags-nkognit0.mp4"
    ),
    "title": "Epic Dota2 gameplay by Nkognit0",
}

animation_data = {
    # For some reason, if we don't define filename explicitly,
    # animation is sent as file.
    "source": HttpUrl(
        f"{EXAMPLE_ATTACHMENT_SOURCE}/hong-kong-simplyart4794.gif"
    ),
    "title": "Hong Kong skyscraper views by Simplyart4794",
    "filename": "hk.gif",
}

image_data = {
    "source": HttpUrl(f"{EXAMPLE_ATTACHMENT_SOURCE}/deeppavlov.png"),
    "title": "DeepPavlov logo",
}

document_data = {
    "source": HttpUrl(f"{EXAMPLE_ATTACHMENT_SOURCE}/deeppavlov-article.pdf"),
    "title": "DeepPavlov article",
}


# %% [markdown]
"""
The bot below sends different attachments on request.

[Here](%doclink(api,script.core.message)) you can find
all the attachment options available.
"""

# %%
script = {
    GLOBAL: {
        TRANSITIONS: {
            ("main_flow", "location_node"): cnd.exact_match(
                Message("location")
            ),
            ("main_flow", "contact_node"): cnd.exact_match(Message("contact")),
            ("main_flow", "poll_node"): cnd.exact_match(Message("poll")),
            ("main_flow", "sticker_node"): cnd.exact_match(Message("sticker")),
            ("main_flow", "audio_node"): cnd.exact_match(Message("audio")),
            ("main_flow", "video_node"): cnd.exact_match(Message("video")),
            ("main_flow", "animation_node"): cnd.exact_match(
                Message("animation")
            ),
            ("main_flow", "image_node"): cnd.exact_match(Message("image")),
            ("main_flow", "document_node"): cnd.exact_match(
                Message("document")
            ),
            ("main_flow", "voice_message_node"): cnd.exact_match(
                Message("voice message")
            ),
            ("main_flow", "video_message_node"): cnd.exact_match(
                Message("video message")
            ),
            ("main_flow", "media_group"): cnd.exact_match(
                Message("media group")
            ),
        }
    },
    "main_flow": {
        "start_node": {
            TRANSITIONS: {"intro_node": cnd.exact_match(Message("/start"))},
        },
        "intro_node": {
            RESPONSE: Message(
                'Type "location", "contact", "poll", "sticker" '
                + '"audio", "video", "animation", "image", '
                + '"document" or to receive a corresponding attachment!'
            ),
        },
        "location_node": {
            RESPONSE: Message(
                "Here's your location!",
                attachments=[Location(**location_data)],
            ),
        },
        "contact_node": {
            RESPONSE: Message(
                "Here's your contact!",
                attachments=[Contact(**contact_data)],
            ),
        },
        "poll_node": {
            RESPONSE: Message(
                "Here's your poll!",
                attachments=[
                    Poll(
                        question="What is the poll question?",
                        options=[
                            PollOption(text="This one!"),
                            PollOption(text="Not this one :("),
                        ],
                    ),
                ],
            ),
        },
        "sticker_node": {
            RESPONSE: Message(
                "Here's your sticker!",
                attachments=[Sticker(**sticker_data)],
            ),
        },
        "audio_node": {
            RESPONSE: Message(
                "Here's your audio!",
                attachments=[Audio(**audio_data)],
            ),
        },
        "video_node": {
            RESPONSE: Message(
                "Here's your video!",
                attachments=[Video(**video_data)],
            ),
        },
        "animation_node": {
            RESPONSE: Message(
                "Here's your animation!",
                attachments=[Animation(**animation_data)],
            ),
        },
        "image_node": {
            RESPONSE: Message(
                "Here's your image!",
                attachments=[Image(**image_data)],
            ),
        },
        "document_node": {
            RESPONSE: Message(
                "Here's your document!",
                attachments=[Document(**document_data)],
            ),
        },
        "voice_message_node": {
            RESPONSE: Message(
                "Here's your voice message!",
                attachments=[VoiceMessage(source=audio_data["source"])],
            ),
        },
        "video_message_node": {
            RESPONSE: Message(
                "Here's your video message!",
                attachments=[VideoMessage(source=video_data["source"])],
            ),
        },
        "media_group": {
            RESPONSE: Message(
                "Here's your media group!",
                attachments=[
                    MediaGroup(
                        group=[
                            Image(**image_data),
                            Video(**video_data),
                            Animation(**animation_data),
                            Audio(**audio_data),
                        ],
                    )
                ],
            ),
        },
        "fallback_node": {
            RESPONSE: Message(
                "Unknown attachment type, try again! "
                + 'Supported attachments are: "location", '
                + '"contact", "poll", "sticker", "audio", '
                + '"video", "animation", "image" and "document".'
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
