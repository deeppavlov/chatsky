# %% [markdown]
"""
# Discord: 1. Basic

The following tutorial shows how to run a regular DFF script in Discord.
"""

# %pip install dff[discord]

# %%
import os

from dff.script import conditions as cnd
from dff.script import labels as lbl
from dff.script import RESPONSE, TRANSITIONS, Message
from dff.messengers.discord_iface import DiscordInterface
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
            TRANSITIONS: {
                "greeting_node": cnd.exact_match(Message(text="/start"))
            },
        },
        "greeting_node": {
            RESPONSE: Message(text="Hi"),
            TRANSITIONS: {lbl.repeat(): cnd.true()},
        },
        "fallback_node": {
            RESPONSE: Message(text="Please, repeat the request"),
            TRANSITIONS: {
                "greeting_node": cnd.exact_match(Message(text="/start"))
            },
        },
    }
}

# this variable is only for testing
happy_path = (
    (Message(text="/start"), Message(text="Hi")),
    (Message(text="Hi"), Message(text="Hi")),
    (Message(text="Bye"), Message(text="Hi")),
)


# %%
interface = DiscordInterface(token=os.environ["DISCORD_BOT_TOKEN"])


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,
    # The interface can be passed as a pipeline argument.
)

# Add bot to a server of your choise using the following command:
# https://discord.com/api/oauth2/authorize?client_id=1194436390612643921&permissions=40666901510720&scope=bot%20applications.commands

def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
