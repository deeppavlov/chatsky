# %% [markdown]
"""
# 4. Conditions

This example shows how to process Telegram updates in your script
and reuse handler triggers from the `pytelegrambotapi` library.
"""

# %%
import os

from dff.script import TRANSITIONS, RESPONSE

from dff.messengers.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
    message_handler,
    handler,
    UpdateType,
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

Note:
Using `message_handler(...)` is the same as using `handler(target_type=UpdateTypes.MESSAGE, ...)`.

Note:
It is possible to use `cnd.exact_match` as a condition (as seen in previous examples).
However, the functionality of that approach is lacking:
At this moment only two fields of `Message` are set during update processing:

- `text` stores a `text` field of `message` updates
- `commands` stores a `data` field of `callback_query` updates

For more information see example `3_buttons_with_callback.py`.
"""


# %%
# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %%
script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: TelegramMessage(text="Hi"),
            TRANSITIONS: {"node1": message_handler(commands=["start", "restart"])},
        },
        "node1": {
            RESPONSE: TelegramMessage(text="Hi, how are you?"),
            TRANSITIONS: {"node2": handler(target_type=UpdateType.MESSAGE, regexp="fine")},
        },
        "node2": {
            RESPONSE: TelegramMessage(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": message_handler(func=lambda msg: "music" in msg.text)},
        },
        "node3": {
            RESPONSE: TelegramMessage(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": message_handler(func=lambda msg: True)},
        },
        "node4": {
            RESPONSE: TelegramMessage(text="bye"),
            TRANSITIONS: {"node1": message_handler(commands=["start", "restart"])},
        },
        "fallback_node": {
            RESPONSE: TelegramMessage(text="Ooops"),
            TRANSITIONS: {"node1": message_handler(commands=["start", "restart"])},
        },
    }
}


# testing
happy_path = (
    (TelegramMessage(text="/start"), TelegramMessage(text="Hi, how are you?")),
    (
        TelegramMessage(text="I'm fine"),
        TelegramMessage(text="Good. What do you want to talk about?"),
    ),
    (
        TelegramMessage(text="About music"),
        TelegramMessage(text="Sorry, I can not talk about music now."),
    ),
    (TelegramMessage(text="ok"), TelegramMessage(text="bye")),
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


def main():
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    main()
