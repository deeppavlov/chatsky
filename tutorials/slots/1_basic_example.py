# %% [markdown]
"""
# 1. Basic Example

The following tutorial shows basic usage of slots extraction
module packaged with `chatsky`.
"""

# %pip install chatsky

# %%
from chatsky.script import conditions as cnd
from chatsky.script import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITIONS_PROCESSING,
    PRE_RESPONSE_PROCESSING,
    GLOBAL,
    LOCAL,
    Message,
)

from chatsky.pipeline import Pipeline
from chatsky.slots import GroupSlot, RegexpSlot
from chatsky.slots import processing as slot_procs
from chatsky.slots import response as slot_rsp
from chatsky.slots import conditions as slot_cnd

from chatsky.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)

# %% [markdown]
"""
The slots fall into the following category groups:

- Value slots can be used to extract slot values from user utterances.
- Group slots can be used to split value slots into groups
    with an arbitrary level of nesting.

You can build the slot tree by passing the child slot instances as extra fields
of the parent slot. In the following cell, we define two slot groups:

    Group 1: person.username, person.email
    Group 2: friend.first_name, friend.last_name

Currently there are two types of value slots:

- %mddoclink(api,slots.slots,RegexpSlot):
    Extracts slot values via regexp.
- %mddoclink(api,slots.slots,FunctionSlot):
    Extracts slot values with the help of a user-defined function.
"""

# %%
SLOTS = GroupSlot(
    person=GroupSlot(
        username=RegexpSlot(
            regexp=r"username is ([a-zA-Z]+)",
            match_group_idx=1,
        ),
        email=RegexpSlot(
            regexp=r"email is ([a-z@\.A-Z]+)",
            match_group_idx=1,
        ),
    ),
    friend=GroupSlot(
        first_name=RegexpSlot(regexp=r"^[A-Z][a-z]+?(?= )"),
        last_name=RegexpSlot(regexp=r"(?<= )[A-Z][a-z]+"),
    ),
)

# %% [markdown]
"""
The slots module provides several functions for managing slots in-script:

- %mddoclink(api,slots.conditions,slots_extracted):
    Condition for checking if specified slots are extracted.
- %mddoclink(api,slots.processing,extract):
    A processing function that extracts specified slots.
- %mddoclink(api,slots.processing,extract_all):
    A processing function that extracts all slots.
- %mddoclink(api,slots.processing,unset):
    A processing function that marks specified slots as not extracted,
    effectively resetting their state.
- %mddoclink(api,slots.processing,unset_all):
    A processing function that marks all slots as not extracted.
- %mddoclink(api,slots.processing,fill_template):
    A processing function that fills the `response`
    Message text with extracted slot values.
- %mddoclink(api,slots.response,filled_template):
    A response function that takes a Message with a
    format-string text and returns Message
    with its text string filled with extracted slot values.

The usage of all the above functions is shown in the following script:
"""

# %%
script = {
    GLOBAL: {TRANSITIONS: {("username_flow", "ask"): cnd.regexp(r"^[sS]tart")}},
    "username_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {
                "get_slot": slot_procs.extract("person.username")
            },
            TRANSITIONS: {
                ("email_flow", "ask", 1.2): slot_cnd.slots_extracted(
                    "person.username"
                ),
                ("username_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {
            RESPONSE: Message(text="Write your username (my username is ...):"),
        },
        "repeat_question": {
            RESPONSE: Message(
                text="Please, type your username again (my username is ...):"
            )
        },
    },
    "email_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {
                "get_slot": slot_procs.extract("person.email")
            },
            TRANSITIONS: {
                ("friend_flow", "ask", 1.2): slot_cnd.slots_extracted(
                    "person.username", "person.email"
                ),
                ("email_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {
            RESPONSE: Message(text="Write your email (my email is ...):"),
        },
        "repeat_question": {
            RESPONSE: Message(
                text="Please, write your email again (my email is ...):"
            )
        },
    },
    "friend_flow": {
        LOCAL: {
            PRE_TRANSITIONS_PROCESSING: {
                "get_slots": slot_procs.extract("friend")
            },
            TRANSITIONS: {
                ("root", "utter", 1.2): slot_cnd.slots_extracted(
                    "friend.first_name", "friend.last_name", mode="any"
                ),
                ("friend_flow", "repeat_question", 0.8): cnd.true(),
            },
        },
        "ask": {
            RESPONSE: Message(
                text="Please, name me one of your friends: (John Doe)"
            )
        },
        "repeat_question": {
            RESPONSE: Message(
                text="Please, name me one of your friends again: (John Doe)"
            )
        },
    },
    "root": {
        "start": {
            RESPONSE: Message(text=""),
            TRANSITIONS: {("username_flow", "ask"): cnd.true()},
        },
        "fallback": {
            RESPONSE: Message(text="Finishing query"),
            TRANSITIONS: {("username_flow", "ask"): cnd.true()},
        },
        "utter": {
            RESPONSE: slot_rsp.filled_template(
                Message(
                    text="Your friend is {friend.first_name} {friend.last_name}"
                )
            ),
            TRANSITIONS: {("root", "utter_alternative"): cnd.true()},
        },
        "utter_alternative": {
            RESPONSE: Message(
                text="Your username is {person.username}. "
                "Your email is {person.email}."
            ),
            PRE_RESPONSE_PROCESSING: {"fill": slot_procs.fill_template()},
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}

# %%
HAPPY_PATH = [
    (
        Message(text="hi"),
        Message(text="Write your username (my username is ...):"),
    ),
    (
        Message(text="my username is groot"),
        Message(text="Write your email (my email is ...):"),
    ),
    (
        Message(text="my email is groot@gmail.com"),
        Message(text="Please, name me one of your friends: (John Doe)"),
    ),
    (Message(text="Bob Page"), Message(text="Your friend is Bob Page")),
    (
        Message(text="ok"),
        Message(text="Your username is groot. Your email is groot@gmail.com."),
    ),
    (Message(text="ok"), Message(text="Finishing query")),
]

# %%
pipeline = Pipeline.from_script(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    slots=SLOTS,
)

if __name__ == "__main__":
    check_happy_path(
        pipeline, HAPPY_PATH
    )  # This is a function for automatic tutorial running
    # (testing) with HAPPY_PATH

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)
