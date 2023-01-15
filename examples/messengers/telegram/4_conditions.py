# %% [markdown]
"""
# 4. Conditions

This example shows how to process Telegram updates in your script
and reuse handler triggers from the `pytelegrambotapi` library.
"""

# %%
import os

from dff.script import TRANSITIONS, RESPONSE, Message

from dff.messengers.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
)
from dff.pipeline import Pipeline
from dff.messengers.telegram import TelegramMessage
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
In our Telegram module, we adopted the system of filters
available in the `pytelegrambotapi` library.

You can use `message_handler` to filter text messages from telegram in various ways.
Filling the `command` argument will cause the handler to only react to listed commands.
`func` argument on the other hand allows you to define arbitrary conditions.
`regexp` creates a regular expression filter, etc.
"""


# %%
# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %%
script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: TelegramMessage(text=""),
            TRANSITIONS: {
                "node1": messenger.cnd.message_handler(commands=["start", "restart", "init"])
            },
        },
        "node1": {
            RESPONSE: TelegramMessage(text="Hi, how are you?"),
            TRANSITIONS: {"node2": messenger.cnd.message_handler(regexp="fine")},
        },
        "node2": {
            RESPONSE: TelegramMessage(text="Good. What do you want to talk about?"),
            TRANSITIONS: {
                "node3": messenger.cnd.message_handler(func=lambda msg: "music" in msg.text)
            },
        },
        "node3": {
            RESPONSE: TelegramMessage(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": messenger.cnd.message_handler(func=lambda msg: True)},
        },
        "node4": {
            RESPONSE: TelegramMessage(text="bye"),
            TRANSITIONS: {
                "node1": messenger.cnd.message_handler(commands=["start", "restart", "init"])
            },
        },
        "fallback_node": {
            RESPONSE: TelegramMessage(text="Ooops"),
            TRANSITIONS: {
                "node1": messenger.cnd.message_handler(commands=["start", "restart", "init"])
            },
        },
    }
}


# testing
happy_path = (
    (Message(text="/start"), Message(text="Hi, how are you?")),
    (Message(text="I'm fine"), Message(text="Good. What do you want to talk about?")),
    (Message(text="About music"), Message(text="Sorry, I can not talk about music now.")),
    (Message(text="ok"), Message(text="bye")),
)


# %%
interface = PollingTelegramInterface(messenger=messenger)


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,
)


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    pipeline.run()
