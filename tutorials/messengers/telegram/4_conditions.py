# %% [markdown]
"""
# Telegram: 4. Conditions

This tutorial shows how to process Telegram updates in your script
and reuse handler triggers from the `pytelegrambotapi` library.

Here, %mddoclink(api,messengers.telegram)
message `original_message` component used
for graph navigation according to Telegram events.
"""


# %pip install dff[telegram]

# %%
import os

from dff.script import TRANSITIONS, RESPONSE

import dff.script.conditions as cnd
from dff.messengers.telegram import PollingTelegramInterface
from dff.pipeline import Pipeline
from dff.script.core.context import Context
from dff.script.core.message import Message
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
In our Telegram module, we adopted the system of filters
available in the `pytelegrambotapi` library.

- Setting the `update_type` will allow filtering by update type:
  if you want the condition to trigger only on updates of the type
  `edited_message`, set it to `UpdateType.EDITED_MESSAGE`.
  The field defaults to `message`.
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
def check_if_latest_message_test_has_music(ctx: Context, _: Pipeline) -> bool:
    if ctx.last_request is None:
        return False
    if ctx.last_request.original_message is None:
        return False
    if ctx.last_request.original_message.message is None:
        return False
    if ctx.last_request.original_message.message.text is None:
        return False
    return "music" in ctx.last_request.original_message.message.text


# %%
script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: {
                "node1": cnd.any(
                    [
                        cnd.exact_match(Message(text="/start")),
                        cnd.exact_match(Message(text="/restart")),
                    ]
                )
            },
        },
        "node1": {
            RESPONSE: Message(text="Hi, how are you?"),
            TRANSITIONS: {"node2": cnd.regexp("fine")},
        },
        "node2": {
            RESPONSE: Message(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": check_if_latest_message_test_has_music},
        },
        "node3": {
            RESPONSE: Message(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": lambda _, __, ___, ____: True},
            # This condition is true for any type of update
        },
        "node4": {
            RESPONSE: Message(text="bye"),
            TRANSITIONS: {"node1": lambda _, __, ___, ____: True},
            # This condition is true if the last update is of type `message`
        },
        "fallback_node": {
            RESPONSE: Message(text="Ooops"),
            TRANSITIONS: {
                "node1": cnd.any(
                    [
                        cnd.exact_match(Message(text="/start")),
                        cnd.exact_match(Message(text="/restart")),
                    ]
                )
            },
        },
    }
}

# this variable is only for testing
happy_path = (
    (Message(text="/start"), Message(text="Hi, how are you?")),
    (
        Message(text="I'm fine"),
        Message(text="Good. What do you want to talk about?"),
    ),
    (
        Message(text="About music"),
        Message(text="Sorry, I can not talk about music now."),
    ),
    (Message(text="ok"), Message(text="bye")),
    (Message(text="bye"), Message(text="Hi, how are you?")),
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
