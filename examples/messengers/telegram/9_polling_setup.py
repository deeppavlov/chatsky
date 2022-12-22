# %% [markdown]
"""
# 9. Polling Setup

The following example shows how to deploy a DFF bot locally using polling.

"""


# %%
import os

from dff.messengers.telegram.interface import PollingTelegramInterface, TelegramMessenger
from dff.pipeline import Pipeline

from dff.utils.testing.common import is_interactive_mode, run_interactive_mode
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH

# %%
messenger = TelegramMessenger(os.getenv("TG_BOT_TOKEN", "SOMETOKEN"))


# %% [markdown]
"""
`PollingTelegramInterface` can be configured with the same parameters
that are used in the `pytelegrambotapi` library, specifically:
* interval - time between calls to the API.
* allowed updates - updates that should be fetched.
* timeout - general timeout.
* long polling timeout - timeout for polling.
"""


# %%
interface = PollingTelegramInterface(
    messenger=messenger,
    interval=2,
    allowed_updates=["message"],
    timeout=30,
    long_polling_timeout=30,
)


# testing
happy_path = HAPPY_PATH


# %%
pipeline = Pipeline.from_script(
    script=TOY_SCRIPT,  # Actor script object, defined in `.utils` module.
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    context_storage=dict(),
    messenger_interface=interface,  # The interface can be passed as a pipeline argument.
)


if __name__ == "__main__":
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # run in an interactive shell
    else:
        if not os.getenv("TG_BOT_TOKEN"):
            raise RuntimeError("`TG_BOT_TOKEN` variable needs to be set to use TelegramInterface.")
        pipeline.run()
