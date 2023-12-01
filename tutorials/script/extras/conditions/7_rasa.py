# %% [markdown]
"""
# 7. Rasa

In this module, we show how you can get annotations from a RASA NLU server
and reuse them in your script.
"""

# %pip install dff[ext,async]

# %%
import os
from dff.script import (
    Message,
    RESPONSE,
    PRE_TRANSITIONS_PROCESSING,
    GLOBAL,
    TRANSITIONS,
    LOCAL,
)
from dff.script import conditions as cnd

from dff.script.extras.conditions.models.remote_api.rasa_model import RasaModel
from dff.script.extras.conditions import conditions as i_cnd
from dff.pipeline import Pipeline
from dff.messengers.common import CLIMessengerInterface
from dff.utils.testing.common import (
    is_interactive_mode,
    check_happy_path,
    run_interactive_mode,
)


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
    namespace_key="rasa",
)


# %%
script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {
            "get_intents": rasa_model
        },  # get intents on each turn
        # Use the obtained intents in your conditions. Note the namespace key that matches the one
        # passed to the model.
        TRANSITIONS: {
            ("root", "finish", 1.2): i_cnd.has_cls_label(
                "goodbye", namespace="rasa"
            )
        },
    },
    "root": {
        LOCAL: {TRANSITIONS: {("mood", "ask", 1.2): cnd.true()}},
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
            TRANSITIONS: {
                ("mood", "react_good"): i_cnd.has_cls_label(
                    "mood_great", threshold=0.95, namespace="rasa"
                ),
                ("mood", "react_bad"): i_cnd.has_cls_label(
                    "mood_unhappy", threshold=0.99, namespace="rasa"
                ),
                ("mood", "assert"): cnd.true(),
            },
        },
        "assert": {
            RESPONSE: Message(
                text="What you mean is you're feeling down, isn't it?"
            ),
            TRANSITIONS: {
                ("mood", "react_good"): i_cnd.has_cls_label(
                    "deny", threshold=0.95, namespace="rasa"
                ),
                ("mood", "react_bad"): i_cnd.has_cls_label(
                    "affirm", namespace="rasa"
                ),
            },
        },
        "react_good": {
            RESPONSE: Message(
                text="Now that's the right talk! You'd better stay happy and stuff."
            ),
            TRANSITIONS: {("root", "finish"): cnd.true()},
        },
        "react_bad": {
            RESPONSE: Message(
                text="I feel you, fellow human. Watch a good movie, it might help."
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
        run_interactive_mode(pipeline)
        # This runs tutorial in interactive mode.
