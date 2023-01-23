# %% [markdown]
"""
# 8. Webhook Setup

The following example shows how to integrate your bot with the Pipeline API.

Assuming you already have a script to deploy. All you need to do
is to instantiate a TelegramMessenger and pass it to an `Interface` class.
This class uses `CallbackTelegramInterface` that makes your bot accessible
through a public webhook.
"""


# %%
import os

from dff.messengers.telegram import (
    TelegramMessenger,
    CallbackTelegramInterface,
)
from dff.pipeline import Pipeline
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.utils.testing.common import is_interactive_mode


# %%
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %% [markdown]
"""
To set up a webhook, you need a messenger and a web application instance.
This class can be configured with the following parameters:
* app - Flask application. You can pass an application with an arbitrary
    number of pre-configured routes. Created automatically if not set.
* host - application host.
* port - application port.
* endpoint - bot access endpoint.
* full_uri - full public address of the endpoint. HTTPS should be enabled
    for successful configuration.
"""


# %%
interface = CallbackTelegramInterface(messenger=messenger)


# %%
pipeline = Pipeline.from_script(
    script=TOY_SCRIPT,  # Actor script object, defined in `.utils` module.
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,  # The interface can be passed as a pipeline argument.
)


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    pipeline.run()
