# %% [markdown]
"""
# Telegram: 1. Basic

The following tutorial shows how to run a regular DFF script in Telegram.
It asks users for the '/start' command and then loops in one place.

Here, %mddoclink(api,messengers.telegram.interface,PollingTelegramInterface)
class and [python-telegram-bot](https://docs.python-telegram-bot.org/)
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
`PollingMessengerInterface` or `CallbackTelegramInterface`.

`TelegramMessenger` encapsulates the bot logic. The` only required
argument for a bot to run is a token. Some other parameters
(such as host, port, interval, etc.) can be passed as keyword arguments.

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


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    pipeline.run()
