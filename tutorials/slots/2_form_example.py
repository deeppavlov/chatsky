# %% [markdown]
"""
# 2. Form Example

...
"""

# %%
from dff.script import labels as lbl
from dff.script import RESPONSE, TRANSITIONS, PRE_TRANSITIONS_PROCESSING, GLOBAL, LOCAL, Message

from dff.pipeline import Pipeline

from dff.utils.testing import check_happy_path, is_interactive_mode, run_interactive_mode
from dff.script import conditions as cnd

from dff.script import slots
from dff.script.slots.forms import FormState
from dff.script.slots import processing as slot_procs
from dff.script.slots import response as slot_rsp
from dff.script.slots import conditions as slot_cnd


def is_unrelated_intent(ctx, actor):
    return False


RestaurantCuisine = slots.RegexpSlot(
    name="cuisine", regexp=r"([A-Za-z]+) cuisine", match_group_idx=1
)
RestaurantAddress = slots.RegexpSlot(
    name="restaurantaddress", regexp=r"(at|in) (.+)", match_group_idx=2
)
NumberOfPeople = slots.RegexpSlot(name="numberofpeople", regexp=r"[0-9]+")
RestaurantForm = slots.FormPolicy(
    "restaurant",
    {
        RestaurantCuisine.name: [("restaurant", "cuisine")],
        RestaurantAddress.name: [("restaurant", "address")],
        NumberOfPeople.name: [("restaurant", "number")],
    },
)

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
                Message(text="Would you like me to find a {cuisine} cuisine restaurant?")
            ),
            TRANSITIONS: {lbl.forward(1.1): cnd.regexp(r"[yY]es|[yY]eah|[Oo][Kk]|[Ff]ine")},
            PRE_TRANSITIONS_PROCESSING: {
                "reset_form": RestaurantForm.update_state(FormState.INACTIVE),
                "reset_slots": slot_procs.unset([RestaurantAddress.name, NumberOfPeople.name]),
            },  # Explicitly resetting form and slot states
        },
        "offer_accepted": {
            RESPONSE: Message(text="Very well then, processing your request."),
            PRE_TRANSITIONS_PROCESSING: {
                "activate_form": RestaurantForm.update_state(slots.FormState.ACTIVE),
            },
        },
        "form_filled": {
            RESPONSE: slot_rsp.fill_template(
                Message(text="All done, a table for {numberofpeople} has been reserved")
            ),
            TRANSITIONS: {("chitchat", "chat_3", 1.1): cnd.true()},
        },
        "cuisine": {
            RESPONSE: Message(text="What kind of cuisine would you like to have?"),
        },
        "address": {
            RESPONSE: Message(text="In what area would you like to find a restaurant?"),
        },
        "number": {
            RESPONSE: Message(text="How many people would you like to invite?"),
        },
    },
    "chitchat": {
        LOCAL: {TRANSITIONS: {lbl.forward(1): cnd.true()}},
        "chat_1": {RESPONSE: Message(text="How's life?")},
        "chat_2": {
            RESPONSE: Message(text="What kind of cuisine do you like?"),
            TRANSITIONS: {
                ("restaurant", "offer", 1.2): slot_cnd.is_set_all(["cuisine"]),
                ("chitchat", "chat_3", 1.1): cnd.true(),
            },
        },
        "chat_3": {
            RESPONSE: Message(text="Did you like the latest Star Wars film?"),
            TRANSITIONS: {lbl.to_fallback(1.1): cnd.true()},
        },
        "chat_4": {RESPONSE: Message(text="Who do you think will win the Champions League?")},
    },
    "root": {
        "start": {RESPONSE: Message(text=""), TRANSITIONS: {("chitchat", "chat_1", 2): cnd.true()}},
        "fallback": {
            RESPONSE: Message(text="Nice chatting with you!"),
            TRANSITIONS: {("chitchat", "chat_1", 2): cnd.true()},
        },
    },
}

HAPPY_PATH = [
    (Message(text="hi"), Message(text="How's life?")),
    (Message(text="good"), Message(text="What kind of cuisine do you like?")),
    (Message(text="none"), Message(text="Did you like the latest Star Wars film?")),
    (Message(text="yes"), Message(text="Nice chatting with you!")),
    (Message(text="hi"), Message(text="How's life?")),
    (Message(text="good"), Message(text="What kind of cuisine do you like?")),
    (
        Message(text="french cuisine"),
        Message(text="Would you like me to find a french cuisine restaurant?"),
    ),
    (Message(text="yes"), Message(text="Very well then, processing your request.")),
    (Message(text="ok"), Message(text="In what area would you like to find a restaurant?")),
    (Message(text="in London"), Message(text="How many people would you like to invite?")),
    (
        Message(text="3 people"),
        Message(text="All done, a table for 3 has been reserved"),
    ),
    (Message(text="ok"), Message(text="Did you like the latest Star Wars film?")),
    (Message(text="yes"), Message(text="Nice chatting with you!")),
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
