from dff.script import conditions as cnd
from dff.script import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITIONS_PROCESSING,
    PRE_RESPONSE_PROCESSING,
    GLOBAL,
    LOCAL,
    Message,
    Context,
)

from dff.pipeline import Pipeline

from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
)

import dff.script.logic.slots
from dff.script.logic.slots import processing as slot_procs
from dff.script.logic.slots import response as slot_rps
from dff.script.logic.slots import conditions as slot_cnd

# In regexp slot you can define a group that will be extracted. Default is 0: full match.
username_slot = dff.script.logic.slots.RegexpSlot(
    name="username", regexp=r"username is ([a-zA-Z]+)", match_group_idx=1
)
email_slot = dff.script.logic.slots.RegexpSlot(
    name="email", regexp=r"(?<=email is )[a-z@\.A-Z]+", match_group_idx=0
)
person_slot = dff.script.logic.slots.GroupSlot(name="person", children=[username_slot, email_slot])
dff.script.logic.slots.add_slots(person_slot)

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
                ("root", "utter", 1.2): slot_cnd.is_set_all(["person/username", "person/email"]),
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
    "root": {
        "start": {RESPONSE: Message(text=""), TRANSITIONS: {("username_flow", "ask"): cnd.true()}},
        "fallback": {
            RESPONSE: Message(text="Finishing query"),
            TRANSITIONS: {("username_flow", "ask"): cnd.true()},
        },
        "utter": {
            RESPONSE: Message(text="Your username is {person/username}."),
            PRE_RESPONSE_PROCESSING: {"fill": slot_procs.fill_template()},
            TRANSITIONS: {("root", "utter_alternative"): cnd.true()},
        },
        "utter_alternative": {
            RESPONSE: slot_rps.fill_template(Message(text="Your email is {person/email}.")),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}


HAPPY_PATH = [
    ("hi", "Write your username (my username is ...):"),
    ("my username is groot", "Write your email (my email is ...):"),
    ("my email is groot@gmail.com", "Your username is groot."),
    ("ok", "Your email is groot@gmail.com."),
    ("ok", "Finishing query"),
]


# %%
pipeline = Pipeline.from_script(
    script,  # Pipeline script object, defined in `dff.utils.testing.toy_script`.
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
)

# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)  # This is a function for automatic tutorial running
    # (testing) with HAPPY_PATH

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        ctx_id = 0  # 0 will be current dialog (context) identification.
        while True:
            ctx: Context = pipeline(input("Send request: "), ctx_id)
            print(ctx.last_response)
