"""
Webhook
=========

The following example shows how to integrate your bot with the Pipeline API.

Assuming that you already have a script that you need to deploy, all you need to do
is to instantiante a TelegramMessenger and pass it to an `Interface` class.

This class uses `WebhookTelegramInterface` that makes your bot accessible
through a public webhook.
"""
import os

from dff.connectors.messenger.telegram.interface import WebhookTelegramInterface
from dff.connectors.messenger.telegram.messenger import TelegramMessenger

from dff.core.pipeline import Pipeline
from dff.utils.testing.toy_script import TOY_SCRIPT
from dff.utils.testing.common import is_interactive_mode, run_interactive_mode

# Like Telebot, TelegramMessenger only requires a token to run.
# However, all parameters from the Telebot class can be passed as keyword arguments.
messenger = TelegramMessenger(os.getenv("BOT_TOKEN", "SOMETOKEN"))

# Setting up a webhook requires a messenger and a web application instance.
interface = WebhookTelegramInterface(messenger=messenger)

pipeline = Pipeline.from_script(
    script=TOY_SCRIPT,  # Actor script object, defined in `.utils` module.
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    context_storage=dict(),
    messenger_interface=interface,  # The interface can be passed as a pipeline argument.
)

if __name__ == "__main__":
    if not os.getenv("BOT_TOKEN"):
        print("`BOT_TOKEN` variable needs to be set to use TelegramInterface.")
    elif is_interactive_mode():
        run_interactive_mode(pipeline)  # run in an interactive shell
    else:
        pipeline.run()  # run in telegram
