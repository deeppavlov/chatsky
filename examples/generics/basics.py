import logging

import df_engine.conditions as cnd
from df_engine.core import Context, Actor
from df_engine.core.keywords import TRANSITIONS, RESPONSE

from df_generics import Response
from .example_utils import run_test, run_interactive_mode

script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: Response(text=""),
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
        "node1": {
            RESPONSE: Response(text="Hi, how are you?"),
            TRANSITIONS: {"node2": cnd.exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: Response(text="Good. What do you want to talk about?"),
            TRANSITIONS: {"node3": cnd.exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: Response(text="Sorry, I can not talk about music now."),
            TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")},
        },
        "node4": {
            RESPONSE: Response(text="bye"),
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
        "fallback_node": {
            RESPONSE: Response(text="Ooops"),
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
    }
}

testing_dialog = [
    ("Hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),
    ("Hi", "Hi, how are you?"),
    ("stop", "Ooops"),
    ("stop", "Ooops"),
    ("Hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),
]

actor = Actor(
    script=script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node")
)

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    # run_test()
    run_interactive_mode(actor)
