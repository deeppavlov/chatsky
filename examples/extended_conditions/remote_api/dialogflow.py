import os
import logging

from df_engine.core.keywords import RESPONSE, PRE_TRANSITIONS_PROCESSING, GLOBAL, TRANSITIONS, LOCAL
from df_engine.core import Actor
from df_engine import conditions as cnd

from df_extended_conditions.models.remote_api.google_dialogflow_model import GoogleDialogFlowModel
from df_extended_conditions import conditions as i_cnd

from examples import example_utils

logger = logging.getLogger(__name__)

gdf_model = GoogleDialogFlowModel.from_file(filename=os.getenv("GDF_ACCOUNT_JSON", ""), namespace_key="dialogflow")

script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {"get_intents": gdf_model},
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

actor = Actor(script, start_label=("root", "start"), fallback_label=("root", "fallback"))

testing_dialogue = [
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
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    example_utils.run_interactive_mode(actor)


if __name__ == "__main__":
    main()
