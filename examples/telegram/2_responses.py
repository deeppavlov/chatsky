# %% [markdown]
"""
# 2. Responses

This example shows how to use the generic `Response` class provided by DFF.
"""

# %%
import os

import dff.core.engine.conditions as cnd
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from dff.connectors.messenger.telegram import (
    PollingTelegramInterface,
    TelegramMessenger,
)
from dff.core.pipeline import Pipeline
from dff.connectors.messenger.generics import Response
from dff.utils.testing.common import is_interactive_mode, run_interactive_mode


# %% [markdown]
"""
In modern messengers, a single message can include one or several attachments aside from text content.
We handle this by introduding the generic `Response` class that can contain both media and text.
In this example, we only use text content for simplicity.
"""


# %%
# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %%
script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
        "node1": {
            RESPONSE: Response(text="Hi, how are you?"),
            TRANSITIONS: {"node2": cnd.exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: Response(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": cnd.exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: Response(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")},
        },
        "node4": {RESPONSE: Response(text="bye"), TRANSITIONS: {"node1": cnd.exact_match("Hi")}},
        "fallback_node": {
            RESPONSE: Response(text="Ooops"),
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
    }
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
