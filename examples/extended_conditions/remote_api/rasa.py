import logging

from dff.core.engine.core.keywords import RESPONSE, PRE_TRANSITIONS_PROCESSING, GLOBAL, TRANSITIONS, LOCAL
from dff.core.engine.core import Actor
from dff.core.engine import conditions as cnd

from dff.script.logic.extended_conditions.models.remote_api.rasa_model import RasaModel
from dff.script.logic.extended_conditions import conditions as i_cnd

from examples import example_utils

logger = logging.getLogger(__name__)

rasa_model = RasaModel(model="http://localhost:5005", namespace_key="rasa")

script = {
    GLOBAL: {
        PRE_TRANSITIONS_PROCESSING: {"get_intents": rasa_model},
        TRANSITIONS: {("root", "finish", 1.2): i_cnd.has_cls_label("goodbye", namespace="rasa")},
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
                ("mood", "react_good"): i_cnd.has_cls_label("mood_great", threshold=0.95, namespace="rasa"),
                ("mood", "react_bad"): i_cnd.has_cls_label("mood_unhappy", namespace="rasa"),
                ("mood", "assert"): cnd.true(),
            },
        },
        "assert": {
            RESPONSE: "What you mean is you're feeling down, isn't it?",
            TRANSITIONS: {
                ("mood", "react_good"): i_cnd.has_cls_label("deny", threshold=0.95, namespace="rasa"),
                ("mood", "react_bad"): i_cnd.has_cls_label("affirm", namespace="rasa"),
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
    ("i'm rather unhappy", "I feel you, fellow human. Watch a good movie, it might help."),
    ("ok", "Ok, see you soon!"),
    ("hi", "How do you feel today?"),
    ("rather bad", "What you mean is you're feeling down, isn't it?"),
    ("yes", "I feel you, fellow human. Watch a good movie, it might help."),
    ("good", "Ok, see you soon!"),
    ("hi", "How do you feel today?"),
    ("I'm feeling great", "Now that's the right talk! You'd better stay happy and stuff."),
]


def main():
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    example_utils.run_interactive_mode(actor)


if __name__ == "__main__":
    main()
