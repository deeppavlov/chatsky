# %% [markdown]
"""
# 6. HF API

This module explains, how to use web-hosted huggingface models in your conversational services.
"""


# %%
import os

from dff.script.core.keywords import (
    RESPONSE,
    PRE_TRANSITIONS_PROCESSING,
    GLOBAL,
    TRANSITIONS,
    LOCAL,
)
from dff.script import conditions as cnd

from dff.script.extras.conditions.models.remote_api.hf_api_model import HFAPIModel
from dff.script.extras.conditions import conditions as i_cnd
from dff.pipeline import Pipeline
from dff.messengers.common import CLIMessengerInterface
from dff.utils.testing.common import is_interactive_mode, run_interactive_mode


# %% [markdown]
"""
The HuggingFace inference API allows you to use any model
on HuggingFace hub that was made publicly available by its owners.
Pass the model address and an API key to construct the class.

We are using this open source model by Obsei-AI
to demonstrate, how custom classifiers can be easily adapted for use your script.
"""


# %%
api_model = HFAPIModel(
    model="obsei-ai/sell-buy-intent-classifier-bert-mini",
    api_key=os.getenv("HF_API_KEY") or input("Enter HF API key:"),
    namespace_key="hf_api",
)


# %%
script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {"get_intents_1": api_model},  # annotate intents on each turn
        TRANSITIONS: {
            # We get to one of the dialog branches depending on the annotation
            ("service", "buy", 1.2): i_cnd.has_cls_label("LABEL_1", threshold=0.95),
            ("service", "sell", 1.2): i_cnd.has_cls_label("LABEL_0", threshold=0.95),
        },
    },
    "root": {
        LOCAL: {TRANSITIONS: {("service", "offer", 1.2): cnd.true()}},
        "start": {RESPONSE: "Hi!"},
        "fallback": {RESPONSE: "I can't quite get what you mean."},
        "finish": {
            RESPONSE: "Ok, see you soon!",
            TRANSITIONS: {("root", "start", 1.3): cnd.true()},
        },
    },
    "service": {
        "offer": {
            RESPONSE: "Welcome to the e-marketplace. Tell us, what you would like to buy or sell."
        },
        "buy": {RESPONSE: "Unfortunately, the item is out of stock at the moment."},
        "sell": {RESPONSE: "Your advertisement has been registered."},
    },
}


# %%
pipeline = Pipeline.from_script(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting Dff bot..."),
)


# %%
happy_path = [
    ("hi", "Welcome to the e-marketplace. Tell us, what you would like to buy or sell."),
    (
        "I would like to buy a car",
        "Unfortunately, the item is out of stock at the moment.",
    ),
    ("ok", "I can't quite get what you mean."),
    ("ok", "Welcome to the e-marketplace. Tell us, what you would like to buy or sell."),
    (
        "sell a bike",
        "Your advertisement has been registered.",
    ),
    ("goodbye", "I can't quite get what you mean."),
]


# %%
def main():
    if is_interactive_mode():
        run_interactive_mode(pipeline)
    else:
        pipeline.run()


if __name__ == "__main__":
    main()
