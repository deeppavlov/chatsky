# %% [markdown]
"""
# 2. Responses

This example shows how to use the generic `Response` class provided by DFF.
"""

# %%
import os

from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE, GLOBAL, PRE_TRANSITIONS_PROCESSING
from dff.core.engine import conditions as cnd
from dff.connectors.messenger.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
)
from dff.core.pipeline import Pipeline
from dff.connectors.messenger.generics import Response
from dff.utils.testing.common import is_interactive_mode, run_interactive_mode


# %% [markdown]
"""
In our Telegram connector, we adopted the system of filters
available in the `pytelegrambotapi` library.

Aside from `message_handler` and `callback_query_handler`, you can use
other triggers to interact with the api. In this example, we use
handlers of other type as global conditions that trigger a response
from the bot.

Here, we use the following triggers:
* `chat_join_request_handler`: join request is sent to the chat where the bot is.
* `my_chat_member_handler`: triggered when the bot is invited to a chat.
* `inline_handler`: triggered when an inline query is being sent to the bot.

The other available conditions are:
* `channel_post_handler`: new post is created in a channel the bot is subscribed to;
* `edited_channel_post_handler`: post is edited in a channel the bot is subscribed to;
* `shipping_query_handler`: shipping query is sent by the user;
* `pre_checkout_query_handler`: order confirmation is sent by the user;
* `poll_handler`: poll is sent to the chat;
* `poll_answer_handler`: users answered the poll sent by the bot.

You can read more on those in the Telegram documentation or in the docs for the `telebot` library.
"""


# %%
# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %%
script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {
            "logging": lambda ctx, actor: print(ctx.framework_states) or ctx
        },
        TRANSITIONS: {
            ("greeting_flow", "node1"): cnd.any(
                [
                    # say hi when invited to a chat
                    messenger.cnd.chat_join_request_handler(func=lambda x: True),
                    # say hi when someone enters the chat
                    messenger.cnd.my_chat_member_handler(func=lambda x: True),
                ]
            ),
            # send a message when inline query is received
            ("greeting_flow", "node2"): messenger.cnd.inline_handler(
                func=lambda query: print(query) or query.query is not None
            ),
        },
    },
    "greeting_flow": {
        "start_node": {
            RESPONSE: "Bot running",
            TRANSITIONS: {
                "node1": messenger.cnd.message_handler(commands=["start", "restart", "init"])
            },
        },
        "node1": {
            RESPONSE: Response(text="Hi"),
            TRANSITIONS: {"start_node": cnd.true()},
        },
        "node2": {
            RESPONSE: Response(text="Inline query received."),
            TRANSITIONS: {"start_node": cnd.true()},
        },
        "fallback_node": {
            RESPONSE: Response(text="Ooops"),
        },
    },
}


# %%
interface = PollingTelegramInterface(messenger=messenger)


# %%
pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    context_storage=dict(),
    messenger_interface=interface,
)

if __name__ == "__main__":
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    elif is_interactive_mode():
        run_interactive_mode(pipeline)  # run in an interactive shell
    else:
        pipeline.run()  # run in telegram
