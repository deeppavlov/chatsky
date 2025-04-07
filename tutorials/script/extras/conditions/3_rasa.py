# %% [markdown]
"""
# ML Conditions: 3. Rasa

In this module, we show how you can get annotations from a RASA NLU server
and reuse them in your script.
"""

# %pip install chatsky[ml]

# %%
import os

from chatsky import (
    Message,
    RESPONSE,
    GLOBAL,
    TRANSITIONS,
    Transition as Tr,
    LOCAL,
)

from chatsky.ml.models.rasa_model import RasaModel
from chatsky.conditions.ml import HasLabel
from chatsky import Pipeline
from chatsky.messengers.console import CLIMessengerInterface
from chatsky.utils.testing.common import is_interactive_mode, check_happy_path

# %% [markdown]
"""
Create a Rasa model and pass the url of a running RASA server.
You can establish a connection both to a local and to a remote server.
The class documentation shows which parameters can be passed for authorization.

"""


# %%
rasa_model = RasaModel(
    model="http://localhost:5005",
    api_key=os.getenv("RASA_API_KEY", "rasa"),
)


# %%
script = {
    GLOBAL: {
        # Use the obtained intents in your conditions.
        TRANSITIONS: [
            Tr(
                dst=("root", "finish"),
                cnd=HasLabel(label="goodbye", pipeline_model="rasa_model"),
                priority=1.2,
            )
        ]
    },
    "root": {
        LOCAL: {TRANSITIONS: [Tr(dst=("mood", "ask"), cnd=True, priority=1.2)]},
        "start": {RESPONSE: Message(text="Hi!")},
        "fallback": {
            RESPONSE: Message(text="I can't quite get what you mean.")
        },
        "finish": {RESPONSE: Message(text="Ok, see you soon!")},
    },
    "mood": {
        "ask": {
            RESPONSE: Message(text="How do you feel today?"),
            # You can get to different branches depending on the intent values.
            TRANSITIONS: [
                Tr(
                    dst=("mood", "react_good"),
                    cnd=HasLabel(
                        label="mood_great",
                        pipeline_model="rasa_model",
                        threshold=0.95,
                    ),
                ),
                Tr(
                    dst=("mood", "react_bad"),
                    cnd=HasLabel(
                        label="mood_unhappy",
                        pipeline_model="rasa_model",
                        threshold=0.99,
                    ),
                ),
                Tr(dst=("mood", "assert"), cnd=True),
            ],
        },
        "assert": {
            RESPONSE: Message(
                text="What you mean is you're feeling down, isn't it?"
            ),
            TRANSITIONS: [
                Tr(
                    dst=("mood", "react_good"),
                    cnd=HasLabel(
                        label="deny",
                        pipeline_model="rasa_model",
                        threshold=0.95,
                    ),
                ),
                Tr(
                    dst=("mood", "react_bad"),
                    cnd=HasLabel(label="affirm", pipeline_model="rasa_model"),
                ),
            ],
        },
        "react_good": {
            RESPONSE: Message(
                text="Now that's the right talk!"
                " You'd better stay happy and stuff."
            ),
            TRANSITIONS: [Tr(dst=("root", "finish"), cnd=True)],
        },
        "react_bad": {
            RESPONSE: Message(
                text="I feel you, fellow human."
                " Watch a good movie, it might help."
            ),
            TRANSITIONS: [Tr(dst=("root", "finish"), cnd=True)],
        },
    },
}


# %%
pipeline = Pipeline(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting RASA bot..."),
    models={"rasa_model": rasa_model},
)


# %%
happy_path = [
    (Message(text="hi"), Message(text="How do you feel today?")),
    (
        Message(text="i'm rather unhappy"),
        Message(
            text="I feel you, fellow human. Watch a good movie, it might help."
        ),
    ),
    (Message(text="ok"), Message(text="Ok, see you soon!")),
    (Message(text="hi"), Message(text="How do you feel today?")),
    (
        Message(text="rather bad"),
        Message(text="What you mean is you're feeling down, isn't it?"),
    ),
    (
        Message(text="yes"),
        Message(
            text="I feel you, fellow human. Watch a good movie, it might help."
        ),
    ),
    (Message(text="good"), Message(text="Ok, see you soon!")),
    (Message(text="hi"), Message(text="How do you feel today?")),
    (
        Message(text="I'm feeling great"),
        Message(
            text="Now that's the right talk! You'd better stay happy and stuff."
        ),
    ),
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
        pipeline.run()
        # This runs tutorial in interactive mode.
