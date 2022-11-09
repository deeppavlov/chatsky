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

from df_generics import Response

import df_slots
from df_slots import processing as slot_procs
from df_slots import response as slot_rps
from df_slots import conditions as slot_cnd

from examples import example_utils

logger = logging.getLogger(__name__)


# In regexp slot you can define a group that will be extracted. Default is 0: full match.
username_slot = df_slots.RegexpSlot(name="username", regexp=r"username is ([a-zA-Z]+)", match_group_idx=1)
email_slot = df_slots.RegexpSlot(name="email", regexp=r"(?<=email is )[a-z@\.A-Z]+", match_group_idx=0)
person_slot = df_slots.GroupSlot(name="person", children=[username_slot, email_slot])
df_slots.add_slots(person_slot)

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
            RESPONSE: Response(text="Write your username (my username is ...):"),
        },
        "repeat_question": {RESPONSE: Response(text="Please, type your username again (my username is ...):")},
    },
    "email_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {"get_slot": slot_procs.extract(["person/email"])},
            TRANSITIONS: {
                ("root", "utter", 1.2): slot_cnd.is_set_all(["person/username", "person/email"]),
                ("email_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {
            RESPONSE: Response(text="Write your email (my email is ...):"),
        },
        "repeat_question": {RESPONSE: Response(text="Please, write your email again (my email is ...):")},
    },
    "root": {
        "start": {RESPONSE: Response(text=""), TRANSITIONS: {("username_flow", "ask"): cnd.true()}},
        "fallback": {RESPONSE: Response(text="Finishing query"), TRANSITIONS: {("username_flow", "ask"): cnd.true()}},
        "utter": {
            RESPONSE: Response(text="Your username is {person/username}."),
            PRE_RESPONSE_PROCESSING: {"fill": slot_procs.fill_template()},
            TRANSITIONS: {("root", "utter_alternative"): cnd.true()},
        },
        "utter_alternative": {
            RESPONSE: slot_rps.fill_template(Response(text="Your email is {person/email}.")),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}


testing_dialog = [
    ("hi", "Write your username (my username is ...):"),
    ("my username is groot", "Write your email (my email is ...):"),
    ("my email is groot@gmail.com", "Your username is groot."),
    ("ok", "Your email is groot@gmail.com."),
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
