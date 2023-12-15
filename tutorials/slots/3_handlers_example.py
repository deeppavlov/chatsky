# %% [markdown]
"""
# 3. Handler Example

The following module demonstrates the implementation
of custom handler functions that can be used to produce
conditions or responses based on the current slot values.
"""

# %pip install dff

# %%
from dff.script import conditions as cnd
from dff.script import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITIONS_PROCESSING,
    GLOBAL,
    LOCAL,
    Context,
    Message,
)

from dff.pipeline import Pipeline

from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.script import slots
from dff.script.slots import conditions as slot_cnd
from dff.script.slots import processing as slot_procs

pet = slots.GroupSlot(
    name="pet",
    children=[
        slots.GroupSlot(
            name="pet_info",
            children=[
                slots.RegexpSlot(
                    name="sort", regexp=r"(dog|cat)", match_group_idx=1
                ),
                slots.RegexpSlot(
                    name="gender",
                    regexp=r"(she|(?<=[^s])he|^he)",
                    match_group_idx=1,
                ),
                slots.RegexpSlot(
                    name="behaviour", regexp=r"(good|bad)", match_group_idx=1
                ),
            ],
        )
    ],
)

# %% [markdown]
"""
You can use the slot handlers to define custom functions.
These include conditions, responses, and processing routines.
The following function can yield 4 responses depending on slot values:
- Is he a good boy or a bad boy?
- Is she a good girl or a bad girl?
- Is your cat good or is it bad?
- Is your dog good or is it bad?
"""


# %%
def custom_behaviour_question(ctx: Context, pipeline: Pipeline):
    template = "Is {pet/pet_info/gender} a good "
    middle = " or a bad "
    new_template = slots.get_filled_template(
        template, ctx, pipeline, slots=["pet/pet_info/gender"]
    )
    gender = slots.get_values(ctx, pipeline, slots=["pet/pet_info/gender"])[0]
    if gender is None:
        new_template = slots.get_filled_template(
            "Is your {pet/pet_info/sort} good or is it bad?", ctx, pipeline
        )
    elif gender == "he":
        new_template = new_template + "boy" + middle + "boy?"
    else:
        new_template = new_template + "girl" + middle + "girl?"
    return Message(text=new_template)


# %% [markdown]
"""
Another response handler that yields one of two distinct response
values depending on the values of slots.
"""


# %%
def custom_esteem(ctx: Context, pipeline: Pipeline):
    value = slots.get_values(ctx, pipeline, slots=["pet/pet_info/behaviour"])[0]
    if value == "bad":
        return Message(text="Sorry to hear that.")
    else:
        return Message(text="Great to hear that!")


# %%
script = {
    GLOBAL: {TRANSITIONS: {("pet_flow", "ask"): cnd.regexp(r"^[sS]tart")}},
    "pet_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {
                "get_slot": slot_procs.extract(["pet/pet_info/sort"])
            },
            TRANSITIONS: {
                ("gender_flow", "ask", 1.2): slot_cnd.is_set_all(
                    ["pet/pet_info/sort"]
                ),
                ("pet_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {
            RESPONSE: Message(
                text="I heard that you have a pet. Is it a cat, or a dog?"
            ),
        },
        "repeat_question": {
            RESPONSE: Message(text="Seriously, is it a cat, or a dog?")
        },
    },
    "gender_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {
                "get_slot": slot_procs.extract(["pet/pet_info/gender"])
            },
            TRANSITIONS: {
                ("behaviour_flow", "ask", 1.2): slot_cnd.is_set_all(
                    ["pet/pet_info/gender"]
                ),
                ("gender_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {
            RESPONSE: Message(text="Great! Is it a he, or a she?"),
        },
        "repeat_question": {
            RESPONSE: Message(
                text="I mean, is it a he, or a she? Name whatever is closer."
            )
        },
    },
    "behaviour_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {
                "get_slot": slot_procs.extract(["pet/pet_info/behaviour"])
            },
            TRANSITIONS: {
                ("root", "esteem", 1.2): slot_cnd.is_set_all(
                    ["pet/pet_info/behaviour"]
                ),
                ("behaviour_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {RESPONSE: custom_behaviour_question},
        "repeat_question": {RESPONSE: custom_behaviour_question},
    },
    "root": {
        "start": {
            RESPONSE: Message(text=""),
            TRANSITIONS: {("pet_flow", "ask"): cnd.true()},
        },
        "fallback": {
            RESPONSE: Message(text="It's been a nice talk! See you."),
            TRANSITIONS: {("pet_flow", "ask"): cnd.true()},
            PRE_TRANSITIONS_PROCESSING: {"forget": slot_procs.unset(["pet"])},
        },
        "esteem": {
            RESPONSE: custom_esteem,
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}

HAPPY_PATH = [
    (
        Message(text="hi"),
        Message(text="I heard that you have a pet. Is it a cat, or a dog?"),
    ),
    (Message(text="it is a dog"), Message(text="Great! Is it a he, or a she?")),
    (Message(text="he"), Message(text="Is he a good boy or a bad boy?")),
    (Message(text="it's bad"), Message(text="Sorry to hear that.")),
    (Message(text="ok"), Message(text="It's been a nice talk! See you.")),
    (
        Message(text="ok"),
        Message(text="I heard that you have a pet. Is it a cat, or a dog?"),
    ),
    (Message(text="a CAT"), Message(text="Seriously, is it a cat, or a dog?")),
    (Message(text="it's a cat"), Message(text="Great! Is it a he, or a she?")),
    (Message(text="she"), Message(text="Is she a good girl or a bad girl?")),
    (Message(text="she is good"), Message(text="Great to hear that!")),
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
