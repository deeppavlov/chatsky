# %% [markdown]
"""
# Using Hugging Face API Models in Chatsky

This tutorial demonstrates how to integrate web-hosted Hugging Face models
into your conversational services using Chatsky.
We'll build a simple customer service bot that uses intent classification
to route conversations.

## What you'll learn
- How to set up and use Hugging Face API models
- How to integrate ML models into your dialog flow
- How to use intent-based routing conditions

## Prerequisites
- A Hugging Face API key (get one at https://huggingface.co/settings/tokens)
- Basic understanding of Chatsky dialog scripts

## Setup

First, let's import the required modules.
"""

# %pip install chatsky[extended_conditions]

# %%
import os
from chatsky import (
    TRANSITIONS,
    RESPONSE,
    Pipeline,
    Transition as Tr,
    GLOBAL,
    LOCAL,
    Message,
)
from chatsky.utils.testing import (
    is_interactive_mode,
)
from chatsky.conditions.ml import HasLabel
from chatsky.messengers.console import CLIMessengerInterface
from chatsky.ml.models.hf_api_model import HFAPIModel

# %% [markdown]
"""
## Setting up the Hugging Face Model

For this example, we'll use a model trained for sell/buy intent classification.
We're using the 'obsei-ai/sell-buy-intent-classifier-bert-mini' model which is
great for zero-shot classification.

You can easily swap this model with any other classification model from HF Hub,
but make sure you pass right models' labels.

For our model there are
LABEL_0 => "SELLING_INTENT" and LABEL_1 => "BUYING_INTENT".
"""

# %%
api_model = HFAPIModel(
    model="obsei-ai/sell-buy-intent-classifier-bert-mini",
    api_key=os.getenv("HF_API_KEY") or input("Enter HF API key:"),
)


# %%
script = {
    GLOBAL: {
        TRANSITIONS: [
            # We get to one of the dialog branches depending on the annotation
            Tr(
                dst=("service", "buy"),
                priority=1.2,
                cnd=HasLabel(
                    label="LABEL_1",
                    pipeline_model="my_hf_model",
                    threshold=0.95,
                ),
            ),
            Tr(
                dst=("service", "sell"),
                priority=1.2,
                cnd=HasLabel(
                    label="LABEL_0",
                    pipeline_model="my_hf_model",
                    threshold=0.95,
                ),
            ),
        ]
    },
    "root": {
        LOCAL: {
            TRANSITIONS: [Tr(dst=("service", "offer"), priority=1.2, cnd=True)]
        },
        "start": {RESPONSE: Message(text="Hi!")},
        "fallback": {
            RESPONSE: Message(text="I can't quite get what you mean.")
        },
        "finish": {
            RESPONSE: Message(text="Ok, see you soon!"),
            TRANSITIONS: [Tr(dst=("root", "start"), priority=1.3, cnd=True)],
        },
    },
    "service": {
        "offer": {
            RESPONSE: Message(
                text="Welcome to the e-marketplace. Tell us,"
                " what you would like to buy or sell."
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
pipeline = Pipeline(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting Dff bot..."),
    models={"my_hf_model": api_model},
)


# %%
happy_path = [
    (
        Message(text="hi"),
        Message(
            text="Welcome to the e-marketplace. Tell us, "
            "what you would like to buy or sell."
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
            text="Welcome to the e-marketplace. Tell us, what you would like to"
            " buy or sell."
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
    if is_interactive_mode():
        pipeline.run()
