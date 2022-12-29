# %% [markdown]
"""
# 1. Base Example

This example demonstrates how to annotate user phrases using a simple regex model.
The way of using this class is similar to that of other models.
Examples for other models can be found in the same section.

"""


# %%
from pathlib import Path

from dff.script.core.keywords import (
    RESPONSE,
    PRE_TRANSITIONS_PROCESSING,
    GLOBAL,
    TRANSITIONS,
    LOCAL,
)
from dff.script import conditions as cnd

from dff.script.extras.conditions.models.local.classifiers.regex import RegexClassifier, RegexModel
from dff.script.extras.conditions.dataset import Dataset
from dff.script.extras.conditions import conditions as i_cnd
from dff.pipeline import Pipeline
from dff.messengers.common import CLIMessengerInterface
from dff.utils.testing.common import is_interactive_mode


# %% [markdown]
"""
In order to be able to use the extended conditions,
you should instantiate a `Matcher` or a `Classifier`.

Sometimes, a dataset is required to construct the instance.
In those cases, you should import a dataset from a file or define it as a dictionary
and then use the `parse_obj` method of the `Dataset` class.
Examples of well-formed dataset files can be found in the 'data' directory.

The manner of instantiating models is uniform across all types
provided by the module.

It is essential that you pass a `namespace_key` to the model,
as it will be used to access the annotations
inside the `Context` object.
"""


# %%
dataset = Dataset.parse_yaml(Path(__file__).parent.joinpath("data/example.yaml"))
# dataset = Dataset.parse_obj({"items": [..., {"label": "greet", "samples": ["hello", "hi"]}, ...]})

regex_model = RegexClassifier(namespace_key="regex", model=RegexModel(dataset))


# %% [markdown]
"""
The instance of the model is a `Callable`, so you can put it directly to the PROCESSING sections
of a dialogue graph, like you would do with regular functions.

The results will be stored indside the `Context` object in the `framework_states` property.
Conditional functions, like `has_cls_label`, will access those annotations
and compare the predicted label probabilities to a threshold of your choice.
"""


# %%
script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {"get_intents": regex_model},
        TRANSITIONS: {("food", "offer", 1.2): i_cnd.has_cls_label("food")},
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


# %%
happy_path = [
    ("hi", "What would you like me to look up?"),
    ("get something to eat", "Would you like me to look up a restaurant for you?"),
    ("yes", "Sorry, all the restaurants are closed due to COVID restrictions."),
    ("ok", "Ok, see you soon!"),
    ("bye", "Hi!"),
    ("hi", "What would you like me to look up?"),
    ("place to sleep", "I can't quite get what you mean."),
    ("ok", "What would you like me to look up?"),
]


# %%
pipeline = Pipeline.from_script(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting Dff bot..."),
    pre_services=[regex_model],
)


# %%
if __name__ == "__main__" and is_interactive_mode():
    pipeline.run()
