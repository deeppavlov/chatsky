# %% [markdown]
"""
# 4. Sklearn Example

AAAAAAAAAAA
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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from dff.script.extras.conditions.models import SklearnClassifier
from dff.script.extras.conditions.models import SklearnMatcher
from dff.script.extras.conditions.dataset import Dataset
from dff.script.extras.conditions import conditions as i_cnd
from dff.pipeline import Pipeline
from dff.messengers.common import CLIMessengerInterface
from dff.utils.testing.common import is_interactive_mode


# %%
data_path = Path(__file__).parent.joinpath("data/example.jsonl")
common_collection = Dataset.parse_jsonl(data_path)

classifier = SklearnClassifier(
    tokenizer=TfidfVectorizer(stop_words=["to"]),
    model=LogisticRegression(class_weight="balanced"),
    namespace_key="skc",
)


# %% [markdown]
"""
When using sklearn, you have to pass in trained models or initialize the models with your data.
To achieve this, call the `fit` method with your dataset as an argument.
"""


# %%
classifier.fit(common_collection)
matcher = SklearnMatcher(
    tokenizer=TfidfVectorizer(stop_words=["to"]), dataset=common_collection, namespace_key="skm"
)
matcher.fit(common_collection)


# %%
script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {
            "get_labels_1": classifier,
            "get_labels_2": matcher,
        },
        TRANSITIONS: {
            ("food", "offer", 1.2): i_cnd.has_cls_label("food", threshold=0.5, namespace="skc"),
            ("food", "offer", 1.1): i_cnd.has_match(matcher, ["I want to eat"], threshold=0.6),
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
pipeline = Pipeline.from_script(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting Dff bot..."),
)


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
if __name__ == "__main__" and is_interactive_mode():
    pipeline.run()
