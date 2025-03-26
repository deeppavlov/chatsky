# %% [markdown]
"""
# Multiple interfaces
"""

# %pip install dff[telegram]

# %%
import os

from chatsky.messengers import CLIMessengerInterface
from chatsky import conditions as cnd
from chatsky.core import RESPONSE, TRANSITIONS, Message
from chatsky.messengers import TelegramInterface
from chatsky.core import Pipeline
from chatsky.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
"""


# %%
script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: {"greeting_node": cnd.ExactMatch(Message("/start"))},
        },
        "greeting_node": {
            RESPONSE: Message("Check out responses from different interfaces!"),
            TRANSITIONS: {
                "console_node": cnd.FromInterface(CLIMessengerInterface),
                "telegram_node": cnd.FromInterface(TelegramInterface)
            },
        },
        "console_node": {
            RESPONSE: Message("Hi from CLI!"),
            TRANSITIONS: {"greeting_node": True}
        },
        "telegram_node": {
            RESPONSE: Message("Hi from Telegram!"),
            TRANSITIONS: {"greeting_node": True}
        },
        "fallback_node": {
            RESPONSE: Message("Please, repeat the request"),
            TRANSITIONS: {"greeting_node": cnd.ExactMatch(Message("/start"))},
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
telegram_interface = TelegramInterface(token=os.environ["TG_BOT_TOKEN"])

console_interface = CLIMessengerInterface()


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interfaces=[telegram_interface, console_interface],
    # The interface can be passed as a pipeline argument.
)


def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
