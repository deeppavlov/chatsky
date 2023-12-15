# %% [markdown]
"""
# 2. Form Example

The following tutorial shows the way you can utilize the `FormPolicy` class
to enhance the dialog with a greedy form-filling strategy.
"""

# %pip install dff

# %%
from dff.script import labels as lbl
from dff.script import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITIONS_PROCESSING,
    GLOBAL,
    LOCAL,
    Message,
)

from dff.pipeline import Pipeline

from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.script import conditions as cnd

from dff.script import slots
from dff.script.slots.forms import FormState
from dff.script.slots import processing as slot_procs
from dff.script.slots import response as slot_rsp
from dff.script.slots import conditions as slot_cnd

# %% [markdown]
"""
As an initial step, all the slots that belong to the form need to be instantiated.
"""
# %%
restaurant_cuisine = slots.RegexpSlot(
    name="cuisine", regexp=r"([A-Za-z]+) cuisine", match_group_idx=1
)
restaurant_address = slots.RegexpSlot(
    name="restaurantaddress", regexp=r"(at|in) (.+)", match_group_idx=2
)
number_of_people = slots.RegexpSlot(name="numberofpeople", regexp=r"[0-9]+")
# %% [markdown]
"""
Secondly, the ``FormPolicy`` object is instantiated where slot names are
mapped to lists of node names. This allows the form component to manage
the dialog ensuring that the user traverses the nodes used for slot extraction.

Slots will be iterated in order to determine the next transition.
If none is possible, the form policy will suggest a fallback transition.

"""
# %%
restaurant_form = slots.FormPolicy(
    "restaurant",
    {
        restaurant_cuisine.name: [("restaurant", "cuisine")],
        restaurant_address.name: [("restaurant", "address")],
        number_of_people.name: [("restaurant", "number")],
    },
)

# %% [markdown]
"""
Thirdly, `to_next_label` method of the form object is used globally in the script
which leads to the relevant condition being checked at every dialog turn.
If the condition is met, the policy will suggest a transition to one of the
nodes from the mapping.

Priority float number is used for the condition to take precedence in cases
when multiple transition options are possible.

"""
# %%
script = {
    GLOBAL: {
        TRANSITIONS: {
            restaurant_form.to_next_label(1.1): restaurant_form.has_state(
                FormState.ACTIVE
            ),
        },
        PRE_TRANSITIONS_PROCESSING: {
            "extract_cuisine": slot_procs.extract([restaurant_cuisine.name]),
            "extract_address": slot_procs.extract([restaurant_address.name]),
            "extract_number": slot_procs.extract([number_of_people.name]),
        },
    },
    "restaurant": {
        LOCAL: {
            TRANSITIONS: {
                ("chitchat", "chat_3", 0.9): cnd.any(
                    [
                        restaurant_form.has_state(FormState.FAILED),
                        restaurant_form.has_state(FormState.INACTIVE),
                    ]
                ),  # this transition ensures the form loop can be left
                ("restaurant", "form_filled", 0.9): restaurant_form.has_state(
                    FormState.COMPLETE
                ),
            }
        },
        "offer": {
            RESPONSE: slot_rsp.fill_template(
                Message(
                    text="Would you like me to find a {cuisine} cuisine restaurant?"
                )
            ),
            TRANSITIONS: {
                lbl.forward(1.1): cnd.regexp(r"[yY]es|[yY]eah|[Oo][Kk]|[Ff]ine")
            },
            PRE_TRANSITIONS_PROCESSING: {
                "reset_form": restaurant_form.update_state(FormState.INACTIVE),
                "reset_slots": slot_procs.unset(
                    [restaurant_address.name, number_of_people.name]
                ),
            },  # Explicitly resetting form and slot states
        },
        "offer_accepted": {
            RESPONSE: Message(text="Very well then, processing your request."),
            PRE_TRANSITIONS_PROCESSING: {
                "activate_form": restaurant_form.update_state(
                    slots.FormState.ACTIVE
                ),
            },
        },
        "form_filled": {
            RESPONSE: slot_rsp.fill_template(
                Message(
                    text="All done, a table for {numberofpeople} has been reserved"
                )
            ),
            TRANSITIONS: {("chitchat", "chat_3", 1.1): cnd.true()},
        },
        "cuisine": {
            RESPONSE: Message(
                text="What kind of cuisine would you like to have?"
            ),
        },
        "address": {
            RESPONSE: Message(
                text="In what area would you like to find a restaurant?"
            ),
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
        "chat_4": {
            RESPONSE: Message(
                text="Who do you think will win the Champions League?"
            )
        },
    },
    "root": {
        "start": {
            RESPONSE: Message(text=""),
            TRANSITIONS: {("chitchat", "chat_1", 2): cnd.true()},
        },
        "fallback": {
            RESPONSE: Message(text="Nice chatting with you!"),
            TRANSITIONS: {("chitchat", "chat_1", 2): cnd.true()},
        },
    },
}

HAPPY_PATH = [
    (Message(text="hi"), Message(text="How's life?")),
    (Message(text="good"), Message(text="What kind of cuisine do you like?")),
    (
        Message(text="none"),
        Message(text="Did you like the latest Star Wars film?"),
    ),
    (Message(text="yes"), Message(text="Nice chatting with you!")),
    (Message(text="hi"), Message(text="How's life?")),
    (Message(text="good"), Message(text="What kind of cuisine do you like?")),
    (
        Message(text="french cuisine"),
        Message(text="Would you like me to find a french cuisine restaurant?"),
    ),
    (
        Message(text="yes"),
        Message(text="Very well then, processing your request."),
    ),
    (
        Message(text="ok"),
        Message(text="In what area would you like to find a restaurant?"),
    ),
    (
        Message(text="in London"),
        Message(text="How many people would you like to invite?"),
    ),
    (
        Message(text="3 people"),
        Message(text="All done, a table for 3 has been reserved"),
    ),
    (
        Message(text="ok"),
        Message(text="Did you like the latest Star Wars film?"),
    ),
    (Message(text="yes"), Message(text="Nice chatting with you!")),
]

# %%
pipeline = Pipeline.from_script(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
