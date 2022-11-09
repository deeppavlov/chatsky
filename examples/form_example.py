import logging

from df_engine import labels as lbl
from df_engine.core import Actor
from df_engine.core.keywords import LOCAL, PRE_TRANSITIONS_PROCESSING, TRANSITIONS, GLOBAL, RESPONSE
from df_engine import conditions as cnd

import df_slots
from df_slots.forms import FormState
from df_slots.utils import FORM_STORAGE_KEY, SLOT_STORAGE_KEY
from df_slots import processing as slot_procs
from df_slots import response as slot_rsp
from df_slots import conditions as slot_cnd

from examples import example_utils

logger = logging.getLogger(__name__)


def is_unrelated_intent(ctx, actor):
    return False


RestaurantCuisine = df_slots.RegexpSlot(name="cuisine", regexp=r"([A-Za-z]+) cuisine", match_group_idx=1)
RestaurantAddress = df_slots.RegexpSlot(name="restaurantaddress", regexp=r"(at|in) (.+)", match_group_idx=2)
NumberOfPeople = df_slots.RegexpSlot(name="numberofpeople", regexp=r"[0-9]+")
RestaurantForm = df_slots.FormPolicy(
    "restaurant",
    {
        RestaurantCuisine.name: [("restaurant", "cuisine")],
        RestaurantAddress.name: [("restaurant", "address")],
        NumberOfPeople.name: [("restaurant", "number")],
    },
)
df_slots.add_slots([RestaurantCuisine, RestaurantAddress, NumberOfPeople])

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
                    [RestaurantForm.has_state(FormState.FAILED), RestaurantForm.has_state(FormState.INACTIVE)]
                ),  # this transition ensures the form loop can be left
                ("restaurant", "form_filled", 0.9): RestaurantForm.has_state(FormState.COMPLETE),
            }
        },
        "offer": {
            RESPONSE: slot_rsp.fill_template("Would you like me to find a {cuisine} cuisine restaurant?"),
            TRANSITIONS: {lbl.forward(1.1): cnd.regexp(r"[yY]es|[yY]eah|[Oo][Kk]|[Ff]ine")},
            PRE_TRANSITIONS_PROCESSING: {
                "reset_form": RestaurantForm.update_state(FormState.INACTIVE),
                "reset_slots": slot_procs.unset([RestaurantAddress.name, NumberOfPeople.name]),
            },  # Explicitly resetting form and slot states in case the user returns to the node after one order
        },
        "offer_accepted": {
            RESPONSE: "Very well then, processing your request.",
            PRE_TRANSITIONS_PROCESSING: {
                "activate_form": RestaurantForm.update_state(df_slots.FormState.ACTIVE),
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
        "fallback": {RESPONSE: "Nice chatting with you!", TRANSITIONS: {("chitchat", "chat_1", 2): cnd.true()}},
    },
}


actor = Actor(script=script, start_label=("root", "start"), fallback_label=("root", "fallback"))
df_slots.register_storage(actor, SLOT_STORAGE_KEY)
df_slots.register_storage(actor, FORM_STORAGE_KEY)

testing_dialog = [
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


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    example_utils.run_interactive_mode(actor)
