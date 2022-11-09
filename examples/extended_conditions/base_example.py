import logging
from pathlib import Path

from dff.core.engine.core.keywords import RESPONSE, PRE_TRANSITIONS_PROCESSING, GLOBAL, TRANSITIONS, LOCAL
from dff.core.engine.core import Actor
from dff.core.engine import conditions as cnd

from dff.script.logic.extended_conditions.models.local.classifiers.regex import RegexClassifier, RegexModel
from dff.script.logic.extended_conditions.dataset import Dataset
from dff.script.logic.extended_conditions import conditions as i_cnd

import _extended_conditions_utils as example_utils

logger = logging.getLogger(__name__)

"""
In order to be able to use the extended conditions, you should instantiate a matcher or a classifier.

Sometimes, a dataset is required to construct the instance. 
In those cases, you should import a dataset from a file or define it as a dictionary
and then use the `parse_obj` method of the `Dataset` class.
"""

dataset = Dataset.parse_yaml(Path(__file__).parent.joinpath("data/example.yaml"))
# dataset = Dataset.parse_obj({"items": [..., {"label": "greet", "samples": ["hello", "hi"]}, ...]})

regex_model = RegexClassifier(namespace_key="regex", model=RegexModel(dataset))

"""
The instance of the model is a `Callable`, so you can put it directly to the PROCESSING sections
of a dialogue graph, like you would do with regular functions.

The results will be stored indside the `Context` object in the `framework_states` property.
Conditional functions, like `has_cls_label`, will access those annotations
and compare the predicted label probabilities to a threshold of your choice.
"""

script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {"get_intents": regex_model},
        TRANSITIONS: {("food", "offer", 1.2): i_cnd.has_cls_label("food")},
    },
    "root": {
        LOCAL: {TRANSITIONS: {("service", "offer", 1.2): cnd.true()}},
        "start": {RESPONSE: "Hi!"},
        "fallback": {RESPONSE: "I can't quite get what you mean."},
        "finish": {RESPONSE: "Ok, see you soon!", TRANSITIONS: {("root", "start", 1.3): cnd.true()}},
    },
    "service": {"offer": {RESPONSE: "What would you like me to look up?"}},
    "food": {
        "offer": {
            RESPONSE: "Would you like me to look up a restaurant for you?",
            TRANSITIONS: {
                ("food", "no_results", 1.2): cnd.regexp(r"yes|yeah|good|ok|yep"),
                ("root", "finish", 0.8): cnd.true(),
            },
        },
        "no_results": {
            RESPONSE: "Sorry, all the restaurants are closed due to COVID restrictions.",
            TRANSITIONS: {("root", "finish"): cnd.true()},
        },
    },
}

actor = Actor(script, start_label=("root", "start"), fallback_label=("root", "fallback"))


testing_dialogue = [
    ("hi", "What would you like me to look up?"),
    ("get something to eat", "Would you like me to look up a restaurant for you?"),
    ("yes", "Sorry, all the restaurants are closed due to COVID restrictions."),
    ("ok", "Ok, see you soon!"),
    ("bye", "Hi!"),
    ("hi", "What would you like me to look up?"),
    ("place to sleep", "I can't quite get what you mean."),
    ("ok", "What would you like me to look up?"),
]


def main():
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    example_utils.run_interactive_mode(actor)


if __name__ == "__main__":
    main()
