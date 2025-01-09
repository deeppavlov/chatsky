# %% [markdown]
"""
# 2. `RegexpGroupSlot` and `string_format`

The following tutorial shows basic usage of `RegexpGroupSlot`
and `string format` feature of GroupSlot.
"""

# %pip install chatsky

# %%
from chatsky import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITION,
    PRE_RESPONSE,
    GLOBAL,
    LOCAL,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    processing as proc,
    responses as rsp,
)

from chatsky.slots import RegexpSlot, RegexpGroupSlot, GroupSlot

from chatsky.utils.testing import (
    check_happy_path,
    is_interactive_mode,
)

# %% [markdown]
"""
## RegexpGroupSlot extraction

The `RegexpGroupSlot` is a slot type that reuses one regex.search() call for
several slots to save on execution time in specific cases like LLM, where the
amount of get_value() calls is important.

## RegexpGroupSlot arguments

* `regexp` - the regular expression to match with the `ctx.last_request.text`.
* `groups` - a dictionary mapping slot names to group indexes, where numbers
        mean the index of the capture group that was found with `re.search()`
        (like `match_group` in RegexpSlot).
* `default_values` - a dictionary with default values for each slot name in
        case the regexp search fails.

The `RegexpGroupSlot` class is derived from `GroupSlot` class, inheriting
its `string_format()` feature.

## `string_format` usage

You can set `string_format` to change the `__str__` representation of the
`ExtractedValueSlot`. `string_format` can be set to a string, which will
be formatted with Python's `str.format()`, using extracted slots names and
their values as keyword arguments.

The reason this exists at all is so you don't have to specify each and every
child slot name and can now represent a GroupSlot in a pre-determined way.

Here are some examples of `RegexpGroupSlot` and `string_format `use:
"""

# %%
two_numbers_regexp_group_slot = RegexpGroupSlot(
    string_format="Second number is {second_number},"
    "first_number is {first_number}.",
    regexp=r"first number is (\d+)\D*second number is (\d+)",
    groups={"first_number": 1, "second_number": 2},
)

# date -> RegexpGroupSlot.
sub_slots_for_group_slot = {
    "date": RegexpSlot(
        regexp=r"(0?[1-9]|(?:1|2)[0-9]|3[0-1])[\.\/]"
        r"(0?[1-9]|1[0-2])[\.\/](\d{4}|\d{2})",
    ),
    "email": RegexpSlot(
        regexp=r"[\w\.-]+@[\w\.-]+\.\w{2,4}",
    ),
}
string_format_group_slot = GroupSlot(
    string_format="Date is {date}, email is {email}", **sub_slots_for_group_slot
)

SLOTS = {
    "two_numbers_slot": two_numbers_regexp_group_slot,
    "string_format_group_slot": string_format_group_slot,
}

script = {
    GLOBAL: {
        TRANSITIONS: [
            Tr(dst=("username_flow", "ask"), cnd=cnd.Regexp(r"^[sS]tart"))
        ]
    },
    "two_numbers_flow": {
        "ask": {
            RESPONSE: "Write two numbers: ",
            PRE_TRANSITION: {"get_slot": proc.Extract("two_numbers_slot")},
        },
        "answer_node": {
            PRE_RESPONSE: {"get_slot": proc.Extract("two_numbers_slot")}
        },
    },
    "username_flow": {
        LOCAL: {
            PRE_TRANSITION: {"get_slot": proc.Extract("person.username")},
            TRANSITIONS: [
                Tr(
                    dst=("email_flow", "ask"),
                    cnd=cnd.SlotsExtracted("person.username"),
                    priority=1.2,
                ),
                Tr(dst=("username_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {
            RESPONSE: "Write your username (my username is ...):",
        },
        "repeat_question": {
            RESPONSE: "Please, type your username again (my username is ...):",
        },
    },
    "email_flow": {
        LOCAL: {
            PRE_TRANSITION: {"get_slot": proc.Extract("person.email")},
            TRANSITIONS: [
                Tr(
                    dst=("friend_flow", "ask"),
                    cnd=cnd.SlotsExtracted("person.username", "person.email"),
                    priority=1.2,
                ),
                Tr(dst=("email_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {
            RESPONSE: "Write your email (my email is ...):",
        },
        "repeat_question": {
            RESPONSE: "Please, write your email again (my email is ...):",
        },
    },
    "friend_flow": {
        LOCAL: {
            PRE_TRANSITION: {"get_slots": proc.Extract("friend")},
            TRANSITIONS: [
                Tr(
                    dst=("root", "utter"),
                    cnd=cnd.SlotsExtracted(
                        "friend.first_name", "friend.last_name", mode="any"
                    ),
                    priority=1.2,
                ),
                Tr(dst=("friend_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {RESPONSE: "Please, name me one of your friends: (John Doe)"},
        "repeat_question": {
            RESPONSE: "Please, name me one of your friends again: (John Doe)"
        },
    },
    "root": {
        "start": {
            TRANSITIONS: [Tr(dst=("username_flow", "ask"))],
        },
        "fallback": {
            RESPONSE: "Finishing query",
            TRANSITIONS: [Tr(dst=("username_flow", "ask"))],
        },
        "utter": {
            RESPONSE: rsp.FilledTemplate(
                "Your friend is {friend.first_name} {friend.last_name}"
            ),
            TRANSITIONS: [Tr(dst=("root", "utter_alternative"))],
        },
        "utter_alternative": {
            RESPONSE: "Your username is {person.username}. "
            "Your email is {person.email}.",
            PRE_RESPONSE: {"fill": proc.FillTemplate()},
        },
    },
}

# %%
HAPPY_PATH = [
    ("hi", "Write your username (my username is ...):"),
    ("my username is groot", "Write your email (my email is ...):"),
    (
        "my email is groot@gmail.com",
        "Please, name me one of your friends: (John Doe)",
    ),
    ("Bob Page", "Your friend is Bob Page"),
    ("ok", "Your username is groot. Your email is groot@gmail.com."),
    ("ok", "Finishing query"),
]

# %%
pipeline = Pipeline(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    slots=SLOTS,
)

if __name__ == "__main__":
    check_happy_path(
        pipeline, HAPPY_PATH, printout=True
    )  # This is a function for automatic tutorial running
    # (testing) with HAPPY_PATH

    if is_interactive_mode():
        pipeline.run()
