# %% [markdown]
"""
# 3. Rasa

In this module, we show how you can get annotations from a RASA NLU server
and reuse them in your script.
"""

# %pip install chatsky[ml]

# %%
import logging
import os
import dotenv

dotenv.load_dotenv()
from chatsky import (
    Message,
    RESPONSE,
    GLOBAL,
    TRANSITIONS,
    Transition as Tr,
    LOCAL,
)
from chatsky import conditions as cnd

from chatsky.ml.models.rasa_model import RasaModel
from chatsky.conditions.ml import HasLabel
from chatsky import Pipeline
from chatsky.messengers.console import CLIMessengerInterface
from chatsky.utils.testing.common import is_interactive_mode, check_happy_path

logging.basicConfig(level=logging.DEBUG)
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
# script = {
#     GLOBAL: {
#         # Use the obtained intents in your conditions.
#         TRANSITIONS: {
#             ("root", "finish", 1.2): HasLabel(
#                 label="goodbye", pipeline_model="rasa_model"
#             ),
#         },
#     },
#     "root": {
#         LOCAL: {TRANSITIONS: {("mood", "ask", 1.2): cnd.true()}},
#         "start": {RESPONSE: Message(text="Hi!")},
#         "fallback": {
#             RESPONSE: Message(text="I can't quite get what you mean.")
#         },
#         "finish": {RESPONSE: Message(text="Ok, see you soon!")},
#     },
#     "mood": {
#         "ask": {
#             RESPONSE: Message(text="How do you feel today?"),
#             # You can get to different branches depending on the intent values.
#             TRANSITIONS: {
#                 ("mood", "react_good"): HasLabel(
#                     label="mood_great",
#                     pipeline_model="rasa_model",
#                     threshold=0.95,
#                 ),
#                 ("mood", "react_bad"): HasLabel(
#                     label="mood_unhappy",
#                     pipeline_model="rasa_model",
#                     threshold=0.99,
#                 ),
#                 ("mood", "assert"): cnd.true(),
#             },
#         },
#         "assert": {
#             RESPONSE: Message(
#                 text="What you mean is you're feeling down, isn't it?"
#             ),
#             TRANSITIONS: {
#                 ("mood", "react_good"): HasLabel(
#                     label="deny", pipeline_model="rasa_model", threshold=0.95
#                 ),
#                 ("mood", "react_bad"): HasLabel(rasa_model, "affirm"),
#             },
#         },
#         "react_good": {
#             RESPONSE: Message(
#                 text="Now that's the right talk!"
#                 " You'd better stay happy and stuff."
#             ),
#             TRANSITIONS: {("root", "finish"): cnd.true()},
#         },
#         "react_bad": {
#             RESPONSE: Message(
#                 text="I feel you, fellow human."
#                 " Watch a good movie, it might help."
#             ),
#             TRANSITIONS: {("root", "finish"): cnd.true()},
#         },
#     },
# }

script = {
    GLOBAL: {
        # Use the obtained intents in your conditions.
        TRANSITIONS: [
            Tr(
                cnd=HasLabel(label="greet", pipeline_model="rasa_model"),
                dst=("root", "hello"),
                priority=1.2,
            ),
            Tr(
                cnd=HasLabel(
                    label="pattern_money", pipeline_model="rasa_model"
                ),
                dst=("root", "money"),
                priority=1.2,
            ),
        ]
    },
    "root": {
        "start": {RESPONSE: Message(text="Hi!")},
        "hello": {
            RESPONSE: Message(text="Hello! How can I help you today?"),
            TRANSITIONS: [
                Tr(cnd=True, dst=("root", "start")),
            ],
        },
        "money": {
            RESPONSE: Message(text="I can help you with money transfer."),
            TRANSITIONS: [
                Tr(cnd=True, dst=("root", "start")),
            ],
        },
        "fallback": {
            RESPONSE: Message(text="I can't quite get what you mean."),
            TRANSITIONS: [
                Tr(cnd=True, dst=("root", "start")),
            ],
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
    # check_happy_path(
    #     pipeline,
    #     happy_path,
    # )  # This is a function for automatic tutorial
    # running (testing tutorial) with `happy_path`.

    # Run tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set.
    if is_interactive_mode():
        pipeline.run()
        # This runs tutorial in interactive mode.
