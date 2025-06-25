# %% [markdown]
"""
# Telegram: 1. Basic

The following tutorial shows how to run a regular Chatsky script in Telegram.
It asks users for the '/start' command and then loops in one place.

Here, %mddoclink(api,messengers.telegram.interface,LongpollingInterface)
class and [python-telegram-bot](https://docs.python-telegram-bot.org/)
library are used for accessing telegram API in polling mode.

Telegram API token is required to access telegram API.
"""

# %pip install chatsky[telegram]=={chatsky}

# %%
import os

from chatsky import (
    RESPONSE,
    TRANSITIONS,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    destinations as dst,
)

from chatsky.core.message import Message, MessageInitTypes
from chatsky.messengers.telegram import LongpollingInterface
from chatsky.utils.testing.common import is_interactive_mode
from chatsky.core.context import Context
from chatsky.core.script_function import BaseResponse


# %% [markdown]
"""
In order to integrate your script with Telegram, you need an instance of the
%mddoclink(api,messengers.telegram.abstract,_AbstractTelegramInterface) class.
Two of its child subclasses that can be instantiated
are %mddoclink(api,messengers.telegram.interface,LongpollingInterface) and
%mddoclink(api,messengers.telegram.interface,WebhookInterface).
The latter requires a webserver, so here we use long polling interface.

%mddoclink(api,messengers.telegram.abstract,_AbstractTelegramInterface)
encapsulates the bot logic. The only required
argument for a bot to run is a token. Some other parameters
(such as host, port, interval, etc.) can be passed as keyword arguments
(for their specs see [documentations of the child subclasses](
%doclink(api,messengers.telegram.interface)
).

Either of the two interfaces connect the bot to Telegram.
They can be passed directly to a Chatsky `Pipeline` instance.

<div class="alert alert-info">

Note

You can also import `LongpollingInterface`
under the alias of `TelegramInterface` from `chatsky.messengers`:

```python
from chatsky.messengers import TelegramInterface
```

</div>
"""
# %%
interface = LongpollingInterface(token=os.environ["TG_BOT_TOKEN"])

# %% [markdown]
"""
## Metadata access

The %mddoclink(api,messengers.telegram.abstract,TelegramMetadata) class
is designed for convenient access to user data from Telegram.

It provides access to the following information:

1. Information about [user](
https://docs.python-telegram-bot.org/en/stable/telegram.user.html):
    - user_id;
    - first_name;
    - last_name;
    - username;
    - language_code.
2. Information about [chat](
https://docs.python-telegram-bot.org/en/stable/telegram.chat.html):
    - chat_id;
    - chat_type;
    - chat_title.

User's metadata is saved with every request message.
For example, metadata of the most recent request in the context can be
accessed via `ctx.last_request.metadata`.

In this tutorial we create a custom `FirstnameGreeting` response class, which
references user's name in the response message.

For more information about responses, see the
%mddoclink(tutorial,script.core.3_responses) tutorial.
"""


# %%
class FirstnameGreeting(BaseResponse):
    async def call(self, ctx: Context) -> MessageInitTypes:
        return f"Hi, {ctx.last_request.metadata.first_name}!"


# %%
script = {
    "greeting_flow": {
        "start_node": {
            TRANSITIONS: [
                Tr(dst="greeting_node", cnd=cnd.ExactMatch(match="/start"))
            ],
        },
        "greeting_node": {
            RESPONSE: FirstnameGreeting(),
            TRANSITIONS: [Tr(dst=dst.Current())],
        },
        "fallback_node": {
            RESPONSE: "Please, repeat the request",
            TRANSITIONS: [
                Tr(dst="greeting_node", cnd=cnd.ExactMatch(match="/start"))
            ],
        },
    }
}


# %%
pipeline = Pipeline(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,
    # The interface can be passed as a pipeline argument.
)


if __name__ == "__main__":
    if is_interactive_mode():
        # prevent run during doc building
        pipeline.run()
