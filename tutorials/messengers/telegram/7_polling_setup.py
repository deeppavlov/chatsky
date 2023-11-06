# %% [markdown]
"""
# Telegram: 7. Polling Setup

The following tutorial shows how to configure `PollingTelegramInterface`.

See %mddoclink(api,messengers.telegram.interface,PollingTelegramInterface)
for more information.
"""

# %pip install dff[telegram]

# %%
import os

from dff.messengers.telegram.interface import PollingTelegramInterface
from dff.pipeline import Pipeline

from dff.utils.testing.common import is_interactive_mode
from dff.utils.testing.toy_script import TOY_SCRIPT_ARGS, HAPPY_PATH
from telebot.util import update_types


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
    token=os.environ["TG_BOT_TOKEN"],
    interval=2,
    allowed_updates=update_types,
    timeout=30,
    long_polling_timeout=30,
)


# testing
happy_path = HAPPY_PATH


# %%
pipeline = Pipeline.from_script(
    *TOY_SCRIPT_ARGS,
    messenger_interface=interface,
    # The interface can be passed as a pipeline argument
)


def main():
    pipeline.run()


if __name__ == "__main__" and is_interactive_mode():
    # prevent run during doc building
    main()
