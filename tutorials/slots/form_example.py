from dff.script import labels as lbl
from dff.script import RESPONSE, TRANSITIONS, PRE_TRANSITIONS_PROCESSING, GLOBAL, LOCAL, Context

from dff.pipeline import Pipeline

from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
)
from dff.script import conditions as cnd

import dff.script.logic.slots
from dff.script.logic.slots.forms import FormState
from dff.script.logic.slots import processing as slot_procs
from dff.script.logic.slots import response as slot_rsp
from dff.script.logic.slots import conditions as slot_cnd


def is_unrelated_intent(ctx, actor):
    return False


RestaurantCuisine = dff.script.logic.slots.RegexpSlot(
    name="cuisine", regexp=r"([A-Za-z]+) cuisine", match_group_idx=1
)
RestaurantAddress = dff.script.logic.slots.RegexpSlot(
    name="restaurantaddress", regexp=r"(at|in) (.+)", match_group_idx=2
)
NumberOfPeople = dff.script.logic.slots.RegexpSlot(name="numberofpeople", regexp=r"[0-9]+")
RestaurantForm = dff.script.logic.slots.FormPolicy(
    "restaurant",
    {
        RestaurantCuisine.name: [("restaurant", "cuisine")],
        RestaurantAddress.name: [("restaurant", "address")],
        NumberOfPeople.name: [("restaurant", "number")],
    },
)
dff.script.logic.slots.add_slots([RestaurantCuisine, RestaurantAddress, NumberOfPeople])

script = {
    GLOBAL: {
        TRANSITIONS: {
            RestaurantForm.to_next_label(1.1): RestaurantForm.has_state(FormState.ACTIVE),
        },
        PRE_TRANSITIONS_PROCESSING: {
            "extract_cuisine": slot_procs.extract([RestaurantCuisine.name]),
            "extract_address": slot_procs.extract([RestaurantAddress.name]),
            "extract_number": slot_procs.extract([NumberOfPeople.name]),
            "update_form_state": RestaurantForm.update_state(),
        },
    },
    "restaurant": {
        LOCAL: {
            TRANSITIONS: {
                ("chitchat", "chat_3", 0.9): cnd.any(
                    [
                        RestaurantForm.has_state(FormState.FAILED),
                        RestaurantForm.has_state(FormState.INACTIVE),
                    ]
                ),  # this transition ensures the form loop can be left
                ("restaurant", "form_filled", 0.9): RestaurantForm.has_state(FormState.COMPLETE),
            }
        },
        "offer": {
            RESPONSE: slot_rsp.fill_template(
                "Would you like me to find a {cuisine} cuisine restaurant?"
            ),
            TRANSITIONS: {lbl.forward(1.1): cnd.regexp(r"[yY]es|[yY]eah|[Oo][Kk]|[Ff]ine")},
            PRE_TRANSITIONS_PROCESSING: {
                "reset_form": RestaurantForm.update_state(FormState.INACTIVE),
                "reset_slots": slot_procs.unset([RestaurantAddress.name, NumberOfPeople.name]),
            },  # Explicitly resetting form and slot states in case the user returns to the node after one order
        },
        "offer_accepted": {
            RESPONSE: "Very well then, processing your request.",
            PRE_TRANSITIONS_PROCESSING: {
                "activate_form": RestaurantForm.update_state(
                    dff.script.logic.slots.FormState.ACTIVE
                ),
            },
        },
        "form_filled": {
            RESPONSE: slot_rsp.fill_template(
                "All done, a table for {numberofpeople} people will be reserved in due time"
            ),
            TRANSITIONS: {("chitchat", "chat_3", 1.1): cnd.true()},
        },
        "cuisine": {
            RESPONSE: "What kind of cuisine would you like to have?",
        },
        "address": {
            RESPONSE: "In what area would you like to find a restaurant?",
        },
        "number": {
            RESPONSE: "How many people would you like to invite?",
        },
    },
    "chitchat": {
        LOCAL: {TRANSITIONS: {lbl.forward(1): cnd.true()}},
        "chat_1": {RESPONSE: "How's life?"},
        "chat_2": {
            RESPONSE: "What kind of cuisine do you like?",
            TRANSITIONS: {
                ("restaurant", "offer", 1.2): slot_cnd.is_set_all(["cuisine"]),
                ("chitchat", "chat_3", 1.1): cnd.true(),
            },
        },
        "chat_3": {
            RESPONSE: "Did you like the latest Star Wars film?",
            TRANSITIONS: {lbl.to_fallback(1.1): cnd.true()},
        },
        "chat_4": {RESPONSE: "Who do you think will win the Champions League?"},
    },
    "root": {
        "start": {RESPONSE: "", TRANSITIONS: {("chitchat", "chat_1", 2): cnd.true()}},
        "fallback": {
            RESPONSE: "Nice chatting with you!",
            TRANSITIONS: {("chitchat", "chat_1", 2): cnd.true()},
        },
    },
}

HAPPY_PATH = [
    ("hi", "How's life?"),
    ("good", "What kind of cuisine do you like?"),
    ("none", "Did you like the latest Star Wars film?"),
    ("yes", "Nice chatting with you!"),
    ("hi", "How's life?"),
    ("good", "What kind of cuisine do you like?"),
    ("french cuisine", "Would you like me to find a french cuisine restaurant?"),
    ("yes", "Very well then, processing your request."),
    ("ok", "In what area would you like to find a restaurant?"),
    ("in London", "How many people would you like to invite?"),
    ("3 people", "All done, a table for 3 people will be reserved in due time"),
    ("ok", "Did you like the latest Star Wars film?"),
    ("yes", "Nice chatting with you!"),
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
