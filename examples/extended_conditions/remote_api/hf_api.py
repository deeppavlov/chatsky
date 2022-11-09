import os
import logging

from dff.core.engine.core.keywords import RESPONSE, PRE_TRANSITIONS_PROCESSING, GLOBAL, TRANSITIONS, LOCAL
from dff.core.engine.core import Actor
from dff.core.engine import conditions as cnd

from dff.script.logic.extended_conditions.models.remote_api.hf_api_model import HFAPIModel
from dff.script.logic.extended_conditions import conditions as i_cnd

import examples.extended_conditions._extended_conditions_utils as example_utils

logger = logging.getLogger(__name__)

# We are using this open source model by Obsei-AI
# to demonstrate, how custom classifiers can be easily adapted for use in dff.script.logic.extended_conditions
api_model = HFAPIModel(
    model="obsei-ai/sell-buy-intent-classifier-bert-mini",
    api_key=os.getenv("HF_API_KEY"),
    namespace_key="hf_api",
)

script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {"get_intents_1": api_model},
        TRANSITIONS: {
            ("service", "buy", 1.2): i_cnd.has_cls_label("LABEL_1", threshold=0.95),
            ("service", "sell", 1.2): i_cnd.has_cls_label("LABEL_0", threshold=0.95),
        },
    },
    "root": {
        LOCAL: {TRANSITIONS: {("service", "offer", 1.2): cnd.true()}},
        "start": {RESPONSE: "Hi!"},
        "fallback": {RESPONSE: "I can't quite get what you mean."},
        "finish": {RESPONSE: "Ok, see you soon!", TRANSITIONS: {("root", "start", 1.3): cnd.true()}},
    },
    "service": {
        "offer": {RESPONSE: "Welcome to the e-marketplace. Tell us, what you would like to buy or sell."},
        "buy": {
            RESPONSE: "We are looking up the requested item... Unfortunately, the item is out of stock at the moment."
        },
        "sell": {RESPONSE: "Your advertisement has been registered. We will inform you of any orders automatically."},
    },
}

actor = Actor(script, start_label=("root", "start"), fallback_label=("root", "fallback"))

testing_dialogue = [
    ("hi", "Welcome to the e-marketplace. Tell us, what you would like to buy or sell."),
    (
        "I would like to buy a car",
        "We are looking up the requested item... Unfortunately, the item is out of stock at the moment.",
    ),
    ("ok", "I can't quite get what you mean."),
    ("ok", "Welcome to the e-marketplace. Tell us, what you would like to buy or sell."),
    ("sell a bike", "Your advertisement has been registered. We will inform you of any orders automatically."),
    ("goodbye", "I can't quite get what you mean."),
]


def main():
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    example_utils.run_interactive_mode(actor)


if __name__ == "__main__":
    main()
