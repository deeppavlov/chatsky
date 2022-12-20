from dff.script.conditions import exact_match
from dff.script import TRANSITIONS, RESPONSE

TOY_SCRIPT = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: "",
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
        "node1": {
            RESPONSE: "Hi, how are you?",
            TRANSITIONS: {"node2": exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: {"node4": exact_match("Ok, goodbye.")},
        },
        "node4": {RESPONSE: "bye", TRANSITIONS: {"node1": exact_match("Hi")}},
        "fallback_node": {
            RESPONSE: "Ooops",
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
    }
}

HAPPY_PATH = (
    ("Hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),
    ("Hi", "Hi, how are you?"),
)
