import logging

from df_engine import conditions as cnd
from df_engine.core.keywords import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITIONS_PROCESSING,
    PRE_RESPONSE_PROCESSING,
    GLOBAL,
    LOCAL,
)
from df_engine.core import Actor

import df_slots
from df_slots import processing as slot_procs
from df_slots import response as slot_rps
from df_slots import conditions as slot_cnd

from examples import example_utils

logger = logging.getLogger(__name__)

# Group 1: person/username, person/email
person_slot = df_slots.GroupSlot(
    name="person",
    children=[
        df_slots.RegexpSlot(name="username", regexp=r"username is ([a-zA-Z]+)", match_group_idx=1),
        df_slots.RegexpSlot(name="email", regexp=r"email is ([a-z@\.A-Z]+)", match_group_idx=1),
    ],
)
# Group 2: friend/first_name, friend/last_name
friend_slot = df_slots.GroupSlot(
    name="friend",
    children=[
        df_slots.RegexpSlot(name="first_name", regexp=r"^[A-Z][a-z]+?(?= )"),
        df_slots.RegexpSlot(name="last_name", regexp=r"(?<= )[A-Z][a-z]+"),
    ],
)
df_slots.add_slots([person_slot, friend_slot])
# ALTERNATE SYNTAX: you can register slots manually.
# from df_slots import slot_types
# username_slot = slot_types.RegexpSlot(name="username", regexp=r"(?<=username is )[a-zA-Z]+")
# person_slot = slot_types.GroupSlot(name="person", children=[username_slot])
# df_slots.root.register_slots([person_slot])


script = {
    GLOBAL: {TRANSITIONS: {("username_flow", "ask"): cnd.regexp(r"^[sS]tart")}},
    "username_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {"get_slot": slot_procs.extract(["person/username"])},
            TRANSITIONS: {
                ("email_flow", "ask", 1.2): slot_cnd.is_set_all(["person/username"]),
                ("username_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {
            RESPONSE: "Write your username (my username is ...):",
        },
        "repeat_question": {RESPONSE: "Please, type your username again (my username is ...):"},
    },
    "email_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {"get_slot": slot_procs.extract(["person/email"])},
            TRANSITIONS: {
                ("friend_flow", "ask", 1.2): slot_cnd.is_set_all(["person/username", "person/email"]),
                ("email_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {
            RESPONSE: "Write your email (my email is ...):",
        },
        "repeat_question": {RESPONSE: "Please, write your email again (my email is ...):"},
    },
    "friend_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {"get_slots": slot_procs.extract(["friend"])},
            TRANSITIONS: {
                ("root", "utter", 1.2): slot_cnd.is_set_any(["friend/first_name", "friend/last_name"]),
                ("friend_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {RESPONSE: "Please, name me one of your friends: (John Doe)"},
        "repeat_question": {RESPONSE: "Please, name me one of your friends again: (John Doe)"},
    },
    "root": {
        "start": {RESPONSE: "", TRANSITIONS: {("username_flow", "ask"): cnd.true()}},
        "fallback": {RESPONSE: "Finishing query", TRANSITIONS: {("username_flow", "ask"): cnd.true()}},
        "utter": {
            RESPONSE: slot_rps.fill_template("Your friend is called {friend/first_name} {friend/last_name}"),
            TRANSITIONS: {("root", "utter_alternative"): cnd.true()},
        },
        "utter_alternative": {
            RESPONSE: "Your username is {person/username}. Your email is {person/email}.",
            PRE_RESPONSE_PROCESSING: {"fill": slot_procs.fill_template()},
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}

testing_dialog = [
    ("hi", "Write your username (my username is ...):"),
    ("my username is groot", "Write your email (my email is ...):"),
    ("my email is groot@gmail.com", "Please, name me one of your friends: (John Doe)"),
    ("Bob Page", "Your friend is called Bob Page"),
    ("ok", "Your username is groot. Your email is groot@gmail.com."),
    ("ok", "Finishing query"),
]

actor = Actor(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
)
df_slots.register_storage(actor, storage=dict())

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    example_utils.run_interactive_mode(actor)
