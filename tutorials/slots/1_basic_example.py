# %% [markdown]
"""
# 1. Basic Example

...
"""

# %%
from dff.script import conditions as cnd
from dff.script import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITIONS_PROCESSING,
    PRE_RESPONSE_PROCESSING,
    GLOBAL,
    LOCAL,
    Message,
)

from dff.pipeline import Pipeline
from dff.script import slots
from dff.script.slots import processing as slot_procs
from dff.script.slots import response as slot_rps
from dff.script.slots import conditions as slot_cnd

from dff.utils.testing import check_happy_path, is_interactive_mode, run_interactive_mode

# %% [markdown]
"""
Instantiating slots.

Group 1: person/username, person/email
"""

# %%
person_slot = slots.GroupSlot(
    name="person",
    children=[
        slots.RegexpSlot(name="username", regexp=r"username is ([a-zA-Z]+)", match_group_idx=1),
        slots.RegexpSlot(name="email", regexp=r"email is ([a-z@\.A-Z]+)", match_group_idx=1),
    ],
)
# Group 2: friend/first_name, friend/last_name
friend_slot = slots.GroupSlot(
    name="friend",
    children=[
        slots.RegexpSlot(name="first_name", regexp=r"^[A-Z][a-z]+?(?= )"),
        slots.RegexpSlot(name="last_name", regexp=r"(?<= )[A-Z][a-z]+"),
    ],
)

# %% [markdown]
"""
Define script.
"""

# %%
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
            RESPONSE: Message(text="Write your username (my username is ...):"),
        },
        "repeat_question": {
            RESPONSE: Message(text="Please, type your username again (my username is ...):")
        },
    },
    "email_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {"get_slot": slot_procs.extract(["person/email"])},
            TRANSITIONS: {
                ("friend_flow", "ask", 1.2): slot_cnd.is_set_all(
                    ["person/username", "person/email"]
                ),
                ("email_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {
            RESPONSE: Message(text="Write your email (my email is ...):"),
        },
        "repeat_question": {
            RESPONSE: Message(text="Please, write your email again (my email is ...):")
        },
    },
    "friend_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {"get_slots": slot_procs.extract(["friend"])},
            TRANSITIONS: {
                ("root", "utter", 1.2): slot_cnd.is_set_any(
                    ["friend/first_name", "friend/last_name"]
                ),
                ("friend_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {RESPONSE: Message(text="Please, name me one of your friends: (John Doe)")},
        "repeat_question": {
            RESPONSE: Message(text="Please, name me one of your friends again: (John Doe)")
        },
    },
    "root": {
        "start": {RESPONSE: Message(text=""), TRANSITIONS: {("username_flow", "ask"): cnd.true()}},
        "fallback": {
            RESPONSE: Message(text="Finishing query"),
            TRANSITIONS: {("username_flow", "ask"): cnd.true()},
        },
        "utter": {
            RESPONSE: slot_rps.fill_template(
                Message(text="Your friend is called {friend/first_name} {friend/last_name}")
            ),
            TRANSITIONS: {("root", "utter_alternative"): cnd.true()},
        },
        "utter_alternative": {
            RESPONSE: Message(
                text="Your username is {person/username}. Your email is {person/email}."
            ),
            PRE_RESPONSE_PROCESSING: {"fill": slot_procs.fill_template()},
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}

# %%
HAPPY_PATH = [
    (Message(text="hi"), Message(text="Write your username (my username is ...):")),
    (Message(text="my username is groot"), Message(text="Write your email (my email is ...):")),
    (
        Message(text="my email is groot@gmail.com"),
        Message(text="Please, name me one of your friends: (John Doe)"),
    ),
    (Message(text="Bob Page"), Message(text="Your friend is called Bob Page")),
    (Message(text="ok"), Message(text="Your username is groot. Your email is groot@gmail.com.")),
    (Message(text="ok"), Message(text="Finishing query")),
]

# %%
pipeline = Pipeline.from_script(
    script,  # Pipeline script object, defined in `dff.utils.testing.toy_script`.
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
