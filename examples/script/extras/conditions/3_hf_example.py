# %% [markdown]
"""
# 3. HF Example

The following example show how to use HuggingFace models
for annotating user phrases.
"""


# %%
from pathlib import Path

from transformers import AutoTokenizer, AutoModelForSequenceClassification

from dff.script.core.keywords import (
    RESPONSE,
    PRE_TRANSITIONS_PROCESSING,
    GLOBAL,
    TRANSITIONS,
    LOCAL,
)
from dff.script import conditions as cnd

from dff.script.extras.conditions.models import HFClassifier
from dff.script.extras.conditions.models import HFMatcher
from dff.script.extras.conditions.dataset import Dataset
from dff.script.extras.conditions import conditions as i_cnd
from dff.pipeline import Pipeline
from dff.messengers.common import CLIMessengerInterface
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
Thanks to the structure of the HuggingFace library, the `AutoTokenizer` and `AutoModel` classes
will handle downloading and deploying the model for you. You need to instantiante
these classes separately and then pass them to the `Classifier` / `Matcher` instance.

We are using an open source model by Obsei-AI
to demonstrate, how custom classifiers can be easily adapted for use in dff.script.extras.conditions
However, you can use any classification model that is accessible via the Hugging Face hub
Below, we list some of the most popular open-source models that can power your conversational logic

unitary/toxic-bert - toxic speech detection
ProsusAI/finbert - sentiment analysis of financial texts
twitter-roberta-base-irony - irony detection
"""


# %%
tokenizer = AutoTokenizer.from_pretrained("obsei-ai/sell-buy-intent-classifier-bert-mini")
model = AutoModelForSequenceClassification.from_pretrained(
    "obsei-ai/sell-buy-intent-classifier-bert-mini"
)

data_path = Path(__file__).parent.joinpath("data/example.json")
common_label_collection = Dataset.parse_json(data_path)

model_1 = HFClassifier(namespace_key="hf_classifier", tokenizer=tokenizer, model=model)

model_2 = HFMatcher(
    namespace_key="hf_matcher", dataset=common_label_collection, tokenizer=tokenizer, model=model
)


# %%
script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {"get_intents_1": model_1, "get_intents_2": model_2},
        TRANSITIONS: {
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
if __name__ == "__main__" and is_interactive_mode():
    pipeline.run()
