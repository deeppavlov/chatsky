# %% [markdown]
"""
# 2. `RegexpGroupSlot` and `string_format`

The following tutorial shows basic usage of `RegexpGroupSlot`
and `string format` feature of GroupSlot.
"""

# %pip install chatsky

# %%
import re

from chatsky import (
    RESPONSE,
    TRANSITIONS,
    PRE_TRANSITION,
    GLOBAL,
    Pipeline,
    Transition as Tr,
    conditions as cnd,
    processing as proc,
    responses as rsp,
    destinations as dst,
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

Below are some examples of `RegexpGroupSlot` and `string_format `use:
"""

# %%
sub_slots_for_group_slot = {
    "date": RegexpGroupSlot(
        string_format="{day}/{month}/{year}",
        regexp=r"(0?[1-9]|(?:1|2)[0-9]|3[0-1])[\.\/]"
        r"(0?[1-9]|1[0-2])[\.\/](\d{4}|\d{2})",
        groups={"day": 1, "month": 2, "year": 3},
    ),
    "email": RegexpSlot(
        regexp=r"[\w\.-]+@[\w\.-]+\.\w{2,4}",
    ),
}
date_and_email = GroupSlot(
    string_format="Your date of birth is {date}, email is {email}",
    **sub_slots_for_group_slot
)

SLOTS = {
    "date_and_email": date_and_email,
}

script = {
    GLOBAL: {
        TRANSITIONS: [
            Tr(
                dst=("date_and_email_flow", "ask_email"),
                cnd=cnd.Regexp(r"^[sS]tart"),
            ),
        ]
    },
    "date_and_email_flow": {
        "start": {
            TRANSITIONS: [Tr(dst=("date_and_email_flow", "ask_date"))],
        },
        "fallback": {
            RESPONSE: "Finishing query",
            TRANSITIONS: [
                Tr(dst=("date_and_email_flow", "ask_email")),
                Tr(
                    dst=dst.Backward(),
                    cnd=cnd.Regexp(r"back", flags=re.IGNORECASE),
                ),
            ],
        },
        "ask_email": {
            RESPONSE: "Write your email (my email is ...):",
            PRE_TRANSITION: {"get_slot": proc.Extract("date_and_email.email")},
            TRANSITIONS: [
                Tr(
                    dst="ask_email",
                    cnd=cnd.SlotsExtracted("date_and_email.email"),
                )
            ],
        },
        "ask_date": {
            RESPONSE: "Write your date of birth:",
            PRE_TRANSITION: {"get_slot": proc.Extract("date_and_email.date")},
            TRANSITIONS: [
                Tr(
                    dst="answer_node",
                    cnd=cnd.SlotsExtracted("date_and_email.date"),
                )
            ],
        },
        "answer_node": {RESPONSE: rsp.FilledTemplate("{date_and_email}")},
    },
}

# %%
HAPPY_PATH = [
    ("hi", "Write your email (my email is ...):"),
    ("my email is groot@gmail.com", "Write your date of birth:"),
    (
        "my date of birth is 06/10/1984",
        "Your date of birth is 06/10/1984, email is groot@gmail.com",
    ),
    ("ok", "Finishing query"),
    ("start", "Write your email (my email is ...):"),
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
