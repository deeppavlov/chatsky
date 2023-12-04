# %% [markdown]
"""
# 4. Sklearn Tutorial

The following tutorial shows how to use Sklearn models
for annotating user phrases.
"""

# %pip install dff[ext]

# %%
from dff.script import (
    Message,
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
from dff.utils.testing.common import (
    is_interactive_mode,
    check_happy_path,
    run_interactive_mode,
)


# %%
common_label_collection = Dataset.model_validate(
    {
        "items": [
            {
                "label": "hello",
                "samples": ["hello", "hi", "hi there", "hello there"],
            },
            {"label": "goodbye", "samples": ["bye", "see you", "goodbye"]},
            {
                "label": "food",
                "samples": ["something to eat", "have a snack", "have a meal"],
            },
        ]
    }
)
# You can also parse static files using the Dataset structure:
# from pathlib import Path
# common_label_collection= Dataset.parse_jsonl(Path(__file__).parent.joinpath("data/example.jsonl"))

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
classifier.fit(common_label_collection)
matcher = SklearnMatcher(
    tokenizer=TfidfVectorizer(stop_words=["to"]),
    dataset=common_label_collection,
    namespace_key="skm",
)
matcher.fit(common_label_collection)


# %%
script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {
            "get_labels_1": classifier,
            "get_labels_2": matcher,
        },
        TRANSITIONS: {
            ("food", "offer", 1.2): i_cnd.has_cls_label(
                "food", threshold=0.5, namespace="skc"
            ),
            ("food", "offer", 1.1): i_cnd.has_match(
                matcher, ["I want to eat"], threshold=0.6
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
        "offer": {RESPONSE: Message(text="What would you like me to look up?")}
    },
    "food": {
        "offer": {
            RESPONSE: Message(
                text="Would you like me to look up a restaurant for you?"
            ),
            TRANSITIONS: {
                ("food", "no_results", 1.2): cnd.regexp(
                    r"yes|yeah|good|ok|yep"
                ),
                ("root", "finish", 0.8): cnd.true(),
            },
        },
        "no_results": {
            RESPONSE: Message(
                text="Sorry, all the restaurants are closed due to COVID restrictions."
            ),
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
    (Message(text="hi"), Message(text="What would you like me to look up?")),
    (
        Message(text="get something to eat"),
        Message(text="Would you like me to look up a restaurant for you?"),
    ),
    (
        Message(text="yes"),
        Message(
            text="Sorry, all the restaurants are closed due to COVID restrictions."
        ),
    ),
    (Message(text="ok"), Message(text="Ok, see you soon!")),
    (Message(text="bye"), Message(text="Hi!")),
    (Message(text="hi"), Message(text="What would you like me to look up?")),
    (
        Message(text="place to sleep"),
        Message(text="I can't quite get what you mean."),
    ),
    (Message(text="ok"), Message(text="What would you like me to look up?")),
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
