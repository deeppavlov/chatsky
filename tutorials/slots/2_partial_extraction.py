# %% [markdown]
"""
# 2. Partial slot extraction

This tutorial shows advanced options for slot extraction allowing
to extract only some of the slots.
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

from chatsky.slots import RegexpSlot, GroupSlot

from chatsky.utils.testing import (
    check_happy_path,
    is_interactive_mode,
)

# %% [markdown]
"""
## Default behavior

By default, slot extraction will write a value into slot storage regardless
of whether the extraction was successful.
If extraction fails, the slot will be marked as "not extracted"
and its value will be the `default_value` (`None` by default).

If group slot is being extracted, the extraction is considered successful
only if all child slots are successfully extracted.

## Success only extraction

The `Extract` function accepts `success_only` flag which makes it so
that extracted value is not saved unless extraction is successful.

This means that unsuccessfully trying to extract a slot after
it has already been extracted will not overwrite the previously extracted
value.

Note that `success_only` is `True` by default.

## Partial group slot extraction

A group slot marked with `allow_partial_extraction` only saves values
of successfully extracted child slots.
Extracting such group slot is equivalent to extracting every child slot
with the `success_only` flag.

Partially extracted group slot is always considered successfully extracted
for the purposes of `success_only` flag.

## Code explanation

In this example we define two group slots: `person` and `friend`.
Note that in the `friend` slot we set `allow_partial_extraction` to `True`
which allows us to _update_ slot values and not
rewrite them in case we don't get full information at once.

So if we send "John Doe" as a full name and after that send only first name
(e.g. "Mike") the extracted friends name would be "Mike Doe"
and not "Mike default_surname".
"""

# %%
SLOTS = {
    "person": GroupSlot(
        coin_address=RegexpSlot(
            regexp=r"(\b[a-zA-Z0-9]{34}\b)",
            default_value="default_address",
            match_group_idx=1,
            required=True,
        ),
        email=RegexpSlot(
            regexp=r"([\w\.-]+@[\w\.-]+\.\w{2,4})",
            default_value="default_email",
            match_group_idx=1,
        ),
    ),
    "friend": GroupSlot(
        coin_address=RegexpSlot(
            regexp=r"(\b[a-zA-Z0-9]{34}\b)", default_value="default_address"
        ),
        email=RegexpSlot(
            regexp=r"([\w\.-]+@[\w\.-]+\.\w{2,4})",
            default_value="default_email",
        ),
        allow_partial_extraction=True,
    ),
}

script = {
    GLOBAL: {
        TRANSITIONS: [
            Tr(dst=("user_flow", "ask"), cnd=cnd.Regexp(r"^[sS]tart"))
        ]
    },
    "user_flow": {
        LOCAL: {
            PRE_TRANSITION: {
                "get_slots": proc.Extract("person", success_only=False)
            },
            TRANSITIONS: [
                Tr(
                    dst=("root", "utter_user"),
                    cnd=cnd.GroupSlotsExtracted(
                        "person", required=["person.coin_address"]
                    ),
                    priority=1.2,
                ),
                # Tr(dst=("user_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {
            RESPONSE: "Please, send your email and bitcoin address in one message."
        },
        "repeat_question": {
            RESPONSE: "Please, send your bitcoin address and email again."
        },
    },
    "friend_flow": {
        LOCAL: {
            PRE_TRANSITION: {
                "get_slots": proc.Extract("friend", success_only=False)
            },
            TRANSITIONS: [
                Tr(
                    dst=("root", "utter_friend"),
                    cnd=cnd.SlotsExtracted(
                        "friend.coin_address", "friend.email", mode="any"
                    ),
                    priority=1.2,
                ),
                Tr(dst=("friend_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {
            RESPONSE: "Please, send your friends bitcoin address and email"
        },
        "repeat_question": {
            RESPONSE: "Please, send your friends bitcoin address and email again."
        },
    },
    "root": {
        "start": {
            TRANSITIONS: [Tr(dst=("user_flow", "ask"))],
        },
        "fallback": {
            RESPONSE: "Finishing query",
            TRANSITIONS: [Tr(dst=("user_flow", "ask"))],
        },
        "utter_friend": {
            RESPONSE: rsp.FilledTemplate(
                "Your friends address is {friend.coin_address} and email is {friend.email}"
            ),
            TRANSITIONS: [Tr(dst=("friend_flow", "ask"))],
        },
        "utter_user": {
            RESPONSE: "Your bitcoin address is {person.coin_address}. Your email is {person.email}.",
            PRE_RESPONSE: {"fill": proc.FillTemplate()},
            TRANSITIONS: [Tr(dst=("friend_flow", "ask"))],
        },
    },
}

HAPPY_PATH = [
    ("Start", "Please, send your email and bitcoin address in one message."),
    (
        "groot, groot@gmail.com",
        "Your bitcoin address is default_address. Your email is groot@gmail.com.",
    ),
    ("ok", "Please, send your friends name"),
    ("Jonh Doe", "Your friend is Jonh Doe"),
    ("ok", "Please, send your friends name"),
    ("Mike ", "Your friend is Mike Doe"),
]


# %%
pipeline = Pipeline(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    slots=SLOTS,
)


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH, printout=True)

    if is_interactive_mode():
        pipeline.run()
