# %% [markdown]
"""
# 8. Webhook Setup

The following tutorial shows how to use `CallbackTelegramInterface`
that makes your bot accessible through a public webhook.
"""


# %%
import os

from dff.messengers.telegram import (
    CallbackTelegramInterface,
)
from dff.pipeline import Pipeline
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH
from dff.utils.testing.common import is_interactive_mode


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
interface = CallbackTelegramInterface(token=os.getenv("TG_BOT_TOKEN", ""))


# %%
pipeline = Pipeline.from_script(
    script=TOY_SCRIPT,  # Actor script object, defined in `.utils` module.
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    messenger_interface=interface,  # The interface can be passed as a pipeline argument.
)

# testing
happy_path = HAPPY_PATH


def main():
    if not os.getenv("TG_BOT_TOKEN"):
        print("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():  # prevent run during doc building
    main()
