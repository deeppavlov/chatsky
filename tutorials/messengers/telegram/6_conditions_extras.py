# %% [markdown]
"""
# Telegram: 6. Conditions Extras

This tutorial shows how to use additional update filters
inherited from the `pytelegrambotapi` library.

Here, %mddoclink(api,messengers.telegram)
message `original_message` component
is used for telegram message type checking.
"""


# %pip install dff[telegram]

# %%
import os

from dff.script import TRANSITIONS, RESPONSE, GLOBAL
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

Aside from `MESSAGE` you can use
other triggers to interact with the api. In this tutorial, we use
handlers of other type as global conditions that trigger a response
from the bot.

Here, we use the following triggers:

* `chat_join_request`: join request is sent to the chat where the bot is.
* `my_chat_member`: triggered when the bot is invited to a chat.
* `inline_query`: triggered when an inline query is being sent to the bot.

The other available conditions are:

* `channel_post`: new post is created in a channel the bot is subscribed to;
* `edited_channel_post`: post is edited in a channel the bot is subscribed to;
* `shipping_query`: shipping query is sent by the user;
* `pre_checkout_query`: order confirmation is sent by the user;
* `poll`: poll is sent to the chat;
* `poll_answer`: users answered the poll sent by the bot.

You can read more on those in the Telegram documentation
or in the docs for the `telebot` library.
"""


# %%
def check_if_latest_message_is_new_chat_member(
    ctx: Context, _: Pipeline
) -> bool:
    if ctx.last_request is None:
        return False
    if ctx.last_request.original_message is None:
        return False
    if ctx.last_request.original_message.message is None:
        return False
    return (
        ctx.last_request.original_message.message.new_chat_members is not None
    )


def check_if_latest_message_is_callback_query(
    ctx: Context, _: Pipeline
) -> bool:
    if ctx.last_request is None:
        return False
    if ctx.last_request.original_message is None:
        return False
    return ctx.last_request.original_message.inline_query is not None


# %%
script = {
    GLOBAL: {
        TRANSITIONS: {
            # say hi when someone enters the chat
            (
                "greeting_flow",
                "node1",
            ): check_if_latest_message_is_new_chat_member,
            # send a message when inline query is received
            (
                "greeting_flow",
                "node2",
            ): check_if_latest_message_is_callback_query,
        },
    },
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
            RESPONSE: Message(text="Hi"),
            TRANSITIONS: {"start_node": cnd.true()},
        },
        "node2": {
            RESPONSE: Message(text="Inline query received."),
            TRANSITIONS: {"start_node": cnd.true()},
        },
        "fallback_node": {
            RESPONSE: Message(text="Ooops"),
        },
    },
}


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
