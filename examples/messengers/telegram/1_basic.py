# %% [markdown]
"""
# 1. Basic

The following example shows how to run a regular DFF script in Telegram.
It asks users for the '/start' command and then loops in one place.
"""


# %%
import os

from dff.script import conditions as cnd
from dff.script import labels as lbl
from dff.script import RESPONSE, TRANSITIONS
from dff.messengers.telegram import PollingTelegramInterface, TelegramMessenger, TelegramMessage
from dff.pipeline import Pipeline
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
In order to integrate your script with Telegram, you need an instance of
`TelegramMessenger` class and one of the following interfaces:
`PollingMessengerInterface` or `WebhookMessengerInterface`.

`TelegramMessenger` encapsulates the bot logic.
Like Telebot, `TelegramMessenger` only requires a token to run.
However, all parameters from the Telebot class can be passed as keyword arguments.

The two interfaces connect the bot to Telegram. They can be passed directly
to the DFF `Pipeline` instance.
"""


# %%
script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: TelegramMessage(text=""),
            TRANSITIONS: {"greeting_node": cnd.exact_match("/start")},
        },
        "greeting_node": {
            RESPONSE: TelegramMessage(text="Hi"),
            TRANSITIONS: {lbl.repeat(): cnd.true()},
        },
        "fallback_node": {
            RESPONSE: TelegramMessage(text="Please, repeat the request"),
            TRANSITIONS: {"greeting_node": cnd.exact_match("/start")},
        },
    }
}


# %%
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))
interface = PollingTelegramInterface(messenger=messenger)


# %%
pipeline = Pipeline.from_script(
    script=script,  # Actor script object
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,  # The interface can be passed as a pipeline argument.
)


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    pipeline.run()
