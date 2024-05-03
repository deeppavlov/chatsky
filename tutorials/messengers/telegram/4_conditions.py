# %% [markdown]
"""
# Telegram: 4. Conditions

This tutorial shows how to process Telegram updates in your script
and reuse handler triggers from the `pytelegrambotapi` library.

Here, %mddoclink(api,messengers.telegram.messenger,telegram_condition)
function is used for graph navigation according to Telegram events.
"""


# %pip install dff[telegram]

# %%
import os

from dff.script import TRANSITIONS, RESPONSE

from dff.messengers.telegram import (
    PollingTelegramInterface,
    telegram_condition,
    UpdateType,
)
from dff.pipeline import Pipeline
from dff.messengers.telegram import TelegramMessage
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
In our Telegram module, we adopted the system of filters
available in the `pytelegrambotapi` library.

You can use `telegram_condition` to filter
text messages from telegram in various ways.

- Setting the `update_type` will allow filtering by update type:
  if you want the condition to trigger only on updates of the type
  `edited_message`, set it to `UpdateType.EDITED_MESSAGE`.
  The field defaults to `message`.
- Setting the `command` argument will cause
  the telegram_condition to only react to listed commands.
- `func` argument on the other hand allows you to define arbitrary conditions.
- `regexp` creates a regular expression filter, etc.

Note:
It is possible to use `cnd.exact_match` as a condition
(as seen in previous tutorials). However, the functionality
of that approach is lacking:

At this moment only two fields of `Message` are set during update processing:

- `text` stores the `text` field of `message` updates
- `callback_query` stores the `data` field of `callback_query` updates

For more information see tutorial `3_buttons_with_callback.py`.
"""


# %%
script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: {
                "node1": telegram_condition(commands=["start", "restart"])
            },
        },
        "node1": {
            RESPONSE: TelegramMessage(text="Hi, how are you?"),
            TRANSITIONS: {
                "node2": telegram_condition(
                    update_type=UpdateType.MESSAGE, regexp="fine"
                )
            },
            # this is the same as
            # TRANSITIONS: {"node2": telegram_condition(regexp="fine")},
        },
        "node2": {
            RESPONSE: TelegramMessage(
                text="Good. What do you want to talk about?"
            ),
            TRANSITIONS: {
                "node3": telegram_condition(
                    func=lambda msg: "music" in msg.text
                )
            },
        },
        "node3": {
            RESPONSE: TelegramMessage(
                text="Sorry, I can not talk about music now."
            ),
            TRANSITIONS: {
                "node4": telegram_condition(update_type=UpdateType.ALL)
            },
            # This condition is true for any type of update
        },
        "node4": {
            RESPONSE: TelegramMessage(text="bye"),
            TRANSITIONS: {"node1": telegram_condition()},
            # This condition is true if the last update is of type `message`
        },
        "fallback_node": {
            RESPONSE: TelegramMessage(text="Ooops"),
            TRANSITIONS: {
                "node1": telegram_condition(commands=["start", "restart"])
            },
        },
    }
}

# this variable is only for testing
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
    (TelegramMessage(text="bye"), TelegramMessage(text="Hi, how are you?")),
)


# %%
interface = PollingTelegramInterface(token=os.environ["TG_BOT_TOKEN"])


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,
)


def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
