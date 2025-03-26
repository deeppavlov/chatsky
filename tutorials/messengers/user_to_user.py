# %% [markdown]
"""
# User-to-user telegram-based interface
"""

# %pip install chatsky[telegram]

# %%
from asyncio import Lock
from os import environ

from chatsky import conditions as cnd, destinations as dst, Transition as Tr
from chatsky.core.context import Context
from chatsky.core.script_function import BaseCondition
from chatsky.core import RESPONSE, TRANSITIONS, Message
from chatsky.messengers.telegram import WebhookInterface
from chatsky.core import Pipeline
from chatsky.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
"""


#%%

user_pairs = dict()


class Connect(BaseCondition):
    mutex = Lock()

    async def call(self, ctx: Context) -> bool:
        async with self.mutex:
            if user_pairs.get(ctx.id) is not None:
                ctx.framework_data.last_forward_from = (ctx.pipeline.messenger_interfaces[0], user_pairs[ctx.id])
                return True
            unmatched = [user for user, peer in user_pairs.items() if peer is not None]
            if len(unmatched) > 0:
                peer = unmatched.pop()
                user_pairs[peer] = ctx.id
                user_pairs[ctx.id] = peer
                ctx.framework_data.last_forward_from = (ctx.pipeline.messenger_interfaces[0], user_pairs[ctx.id])
                return True
            else:
                user_pairs[ctx.id] = None
            return False


# %%

script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: [
                Tr(cnd=cnd.ExactMatch(Message("/start")))
            ],
        },
        "greeting_node": {
            RESPONSE: Message("Type /connect to connect to another user!"),
            TRANSITIONS: [
                Tr(
                    cnd=cnd.ExactMatch(Message("/connect")),
                    dst="initializing_node",
                ),
                Tr(dst="fallback_node")
            ],
        },
        "initializing_node": {
            RESPONSE: Message(""),
            TRANSITIONS: [
                # 
            ]
        },
        "talking_node": {
            RESPONSE: Message(),
            TRANSITIONS: [
                Tr(
                    cnd=cnd.ExactMatch(Message("/disconnect")),
                    dst="greeting_node",
                ),
                Tr(
                    dst=dst.Current(),
                )
            ]
        },
        "fallback_node": {
            RESPONSE: Message("Please, repeat the request"),
            TRANSITIONS: [
                Tr(dst="greeting_node")
            ],
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
pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interfaces=WebhookInterface(token=environ["TG_BOT_TOKEN"]),
)


def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
