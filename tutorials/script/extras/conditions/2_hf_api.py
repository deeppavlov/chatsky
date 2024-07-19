# %% [markdown]
"""
# 6. HF API

This module explains, how to use web-hosted huggingface models in your conversational services.
"""

# %pip install dff[ext,async]

# %%
import os
from chatsky.script import (
    Message,
    RESPONSE,
    PRE_TRANSITIONS_PROCESSING,
    GLOBAL,
    TRANSITIONS,
    LOCAL,
)
from chatsky.script import conditions as cnd

from chatsky.script.conditions.llm_conditions.models.remote_api.hf_api_model import (
    HFAPIModel,
)
from chatsky.script.conditions.llm_conditions import conditions as i_cnd
from chatsky.pipeline import Pipeline
from chatsky.messengers.console import CLIMessengerInterface
from chatsky.utils.testing.common import (
    is_interactive_mode,
    check_happy_path,
    run_interactive_mode,
)


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
)


# %%
script = {
    GLOBAL: {
        TRANSITIONS: {
            # We get to one of the dialog branches depending on the annotation
            ("service", "buy", 1.2): i_cnd.has_cls_label(
                api_model, "LABEL_1", threshold=0.95
            ),
            ("service", "sell", 1.2): i_cnd.has_cls_label(
                api_model, "LABEL_0", threshold=0.95
            ),
        },
    },
    "root": {
        LOCAL: {TRANSITIONS: {("service", "offer", 1.2): cnd.true()}},
        "start": {RESPONSE: Message(text="Hi!")},
        "fallback": {
            RESPONSE: Message(text="I can't quite get what you mean.")
        },
        "finish": {
            RESPONSE: Message(text="Ok, see you soon!"),
            TRANSITIONS: {("root", "start", 1.3): cnd.true()},
        },
    },
    "service": {
        "offer": {
            RESPONSE: Message(
                text="Welcome to the e-marketplace. Tell us, what you would like to buy or sell."
            )
        },
        "buy": {
            RESPONSE: Message(
                text="Unfortunately, the item is out of stock at the moment."
            )
        },
        "sell": {
            RESPONSE: Message(text="Your advertisement has been registered.")
        },
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
    (
        Message(text="hi"),
        Message(
            text="Welcome to the e-marketplace. Tell us, what you would like to buy or sell."
        ),
    ),
    (
        Message(text="I would like to buy a car"),
        Message(text="Unfortunately, the item is out of stock at the moment."),
    ),
    (Message(text="ok"), Message(text="I can't quite get what you mean.")),
    (
        Message(text="ok"),
        Message(
            text="Welcome to the e-marketplace. Tell us, what you would like to buy or sell."
        ),
    ),
    (
        Message(text="sell a bike"),
        Message(text="Your advertisement has been registered."),
    ),
    (Message(text="goodbye"), Message(text="I can't quite get what you mean.")),
]


# %%
if __name__ == "__main__":
    check_happy_path(
        pipeline,
        happy_path,
    )  # This is a function for automatic tutorial
    # running (testing tutorial) with `happy_path`.

    # Run tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set.
    if is_interactive_mode():
        run_interactive_mode(pipeline)
        # This runs tutorial in interactive mode.
