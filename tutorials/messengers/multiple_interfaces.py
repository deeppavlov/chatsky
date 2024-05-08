# %% [markdown]
"""
# Multiple interfaces
"""

# %pip install dff[telegram]

# %%
import os

from dff.messengers.common.interface import CLIMessengerInterface
from dff.script import conditions as cnd
from dff.script import RESPONSE, TRANSITIONS, Message
from dff.messengers.telegram import PollingTelegramInterface
from dff.pipeline import Pipeline
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
"""


# %%
script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: {"greeting_node": cnd.exact_match(Message("/start"))},
        },
        "greeting_node": {
            RESPONSE: Message("Check out responses from different interfaces!"),
            TRANSITIONS: {
                "console_node": cnd.from_interface(CLIMessengerInterface),
                "telegram_node": cnd.from_interface(PollingTelegramInterface)
            },
        },
        "console_node": {
            RESPONSE: Message("Hi from CLI!"),
            TRANSITIONS: {"greeting_node": cnd.true()}
        },
        "telegram_node": {
            RESPONSE: Message("Hi from Telegram!"),
            TRANSITIONS: {"greeting_node": cnd.true()}
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
telegram_interface = PollingTelegramInterface(token=os.environ["TG_BOT_TOKEN"])

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
