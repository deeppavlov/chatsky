# %% [markdown]
"""
# Telegram: 1. Basic

The following tutorial shows how to run a regular DFF script in Telegram.
It asks users for the '/start' command and then loops in one place.

Here, %mddoclink(api,messengers.telegram.interface,PollingTelegramInterface)
class and [telebot](https://pytba.readthedocs.io/en/latest/index.html)
library are used for accessing telegram API in polling mode.

Telegram API token is required to access telegram API.
"""

# %pip install dff[telegram]

# %%
import os

from dff.script import conditions as cnd
from dff.script import labels as lbl
from dff.script import RESPONSE, TRANSITIONS, Message
from dff.messengers.telegram import PollingTelegramInterface
from dff.pipeline import Pipeline
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


# %%
script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: {"greeting_node": cnd.exact_match(Message("/start"))},
        },
        "greeting_node": {
            RESPONSE: Message("Hi"),
            TRANSITIONS: {lbl.repeat(): cnd.true()},
        },
        "fallback_node": {
            RESPONSE: Message("Please, repeat the request"),
            TRANSITIONS: {"greeting_node": cnd.exact_match(Message("/start"))},
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
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,
    # The interface can be passed as a pipeline argument.
)


def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
