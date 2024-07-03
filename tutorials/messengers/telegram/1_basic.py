# %% [markdown]
"""
# Telegram: 1. Basic

The following tutorial shows how to run a regular Chatsky script in Telegram.
It asks users for the '/start' command and then loops in one place.

Here, %mddoclink(api,messengers.telegram.interface,LongpollingInterface)
class and [python-telegram-bot](https://docs.python-telegram-bot.org/)
library are used for accessing telegram API in polling mode.

Telegram API token is required to access telegram API.
"""

# %pip install chatsky[telegram]

# %%
import os

from chatsky.script import conditions as cnd
from chatsky.script import labels as lbl
from chatsky.script import RESPONSE, TRANSITIONS, Message
from chatsky.messengers.telegram import LongpollingInterface
from chatsky.pipeline import Pipeline
from chatsky.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
In order to integrate your script with Telegram, you need an instance of the
%mddoclink(api,messengers.telegram.abstract,_AbstractTelegramInterface) class.
Two of its child subclasses that can be instantiated
are %mddoclink(api,messengers.telegram.interface,LongpollingInterface) and
%mddoclink(api,messengers.telegram.interface,WebhookInterface).
The latter requires a webserver, so here we use long polling interface.

%mddoclink(api,messengers.telegram.abstract,_AbstractTelegramInterface)
encapsulates the bot logic. The only required
argument for a bot to run is a token. Some other parameters
(such as host, port, interval, etc.) can be passed as keyword arguments
(for their specs see [documentations of the child subclasses](
%doclink(api,messengers.telegram.interface)
).

Either of the two interfaces connect the bot to Telegram.
They can be passed directly to a Chatsky `Pipeline` instance.
"""


# %%
script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: {"greeting_node": cnd.exact_match("/start")},
        },
        "greeting_node": {
            RESPONSE: Message("Hi"),
            TRANSITIONS: {lbl.repeat(): cnd.true()},
        },
        "fallback_node": {
            RESPONSE: Message("Please, repeat the request"),
            TRANSITIONS: {"greeting_node": cnd.exact_match("/start")},
        },
    }
}


# %%
interface = LongpollingInterface(token=os.environ["TG_BOT_TOKEN"])


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,
    # The interface can be passed as a pipeline argument.
)


if __name__ == "__main__":
    if is_interactive_mode():
        # prevent run during doc building
        pipeline.run()
