"""
Dialogflow
==========

The example below demonstrates, how to integrate Google Dialogflow into your script logic.
"""
import os

from dff.core.engine.core.keywords import RESPONSE, PRE_TRANSITIONS_PROCESSING, GLOBAL, TRANSITIONS, LOCAL
from dff.core.engine import conditions as cnd

from dff.script.logic.extended_conditions.models.remote_api.google_dialogflow_model import GoogleDialogFlowModel
from dff.script.logic.extended_conditions import conditions as i_cnd
from dff.core.pipeline import Pipeline, CLIMessengerInterface
from dff.utils.testing.common import is_interactive_mode, run_interactive_mode


"""

"""
gdf_model = GoogleDialogFlowModel.from_file(filename=os.getenv("GDF_ACCOUNT_JSON", ""), namespace_key="dialogflow")

script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {"get_intents": gdf_model},  # global processing extracts intents on each turn
        # Intents from Google Dialogflow can be used in conditions to traverse your dialog graph
        TRANSITIONS: {("root", "finish", 1.2): i_cnd.has_cls_label("goodbye", namespace="dialogflow")},
    },
    "root": {
        LOCAL: {TRANSITIONS: {("mood", "ask", 1.2): cnd.true()}},
        "start": {RESPONSE: "Hi!"},
        "fallback": {RESPONSE: "I can't quite get what you mean."},
        "finish": {RESPONSE: "Ok, see you soon!"},
    },
    "mood": {
        "ask": {
            RESPONSE: "How do you feel today?",
            TRANSITIONS: {
                # Here, we use intents to decide which branch of dialog should be picked
                ("mood", "react_good"): i_cnd.has_cls_label("mood_great", threshold=0.95, namespace="dialogflow"),
                ("mood", "react_bad"): i_cnd.has_cls_label("mood_unhappy", namespace="dialogflow"),
                ("mood", "assert"): cnd.true(),
            },
        },
        "assert": {
            RESPONSE: "What you mean is you're feeling down, isn't it?",
            TRANSITIONS: {
                ("mood", "react_good"): i_cnd.has_cls_label("deny", threshold=0.95, namespace="dialogflow"),
                ("mood", "react_bad"): i_cnd.has_cls_label("affirm", namespace="dialogflow"),
            },
        },
        "react_good": {
            RESPONSE: "Now that's the right talk! You'd better stay happy and stuff.",
            TRANSITIONS: {("root", "finish"): cnd.true()},
        },
        "react_bad": {
            RESPONSE: "I feel you, fellow human. Watch a good movie, it might help.",
            TRANSITIONS: {("root", "finish"): cnd.true()},
        },
    },
}

pipeline = Pipeline.from_script(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting Dff bot..."),
)

happy_path = [
    ("hi", "How do you feel today?"),
    ("i'm sad", "I feel you, fellow human. Watch a good movie, it might help."),
    ("ok", "Ok, see you soon!"),
    ("hi", "How do you feel today?"),
    ("rather bad", "What you mean is you're feeling down, isn't it?"),
    ("yes", "I feel you, fellow human. Watch a good movie, it might help."),
    ("good", "Ok, see you soon!"),
    ("hi", "How do you feel today?"),
    ("great", "Now that's the right talk! You'd better stay happy and stuff."),
]


def main():
    if is_interactive_mode():
        run_interactive_mode(pipeline)
    else:
        pipeline.run()


if __name__ == "__main__":
    main()
