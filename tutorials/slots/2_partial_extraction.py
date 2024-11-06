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
## Extracted values

Result of successful slot extraction is the extracted value, *but*
if the extraction fails, the slot will be marked as "not extracted"
and its value will be set to the slot's `default_value` (`None` by default).

If group slot is being extracted, the extraction is considered successful
if and only if all child slots are successfully extracted.

## Success only extraction

The `Extract` function accepts `success_only` flag which makes it so
that extracted value is not saved unless extraction is successful.

This means that unsuccessfully trying to extract a slot will not overwrite
its previously extracted value.

Note that `success_only` is `True` by default.

## Partial group slot extraction

A group slot marked with `allow_partial_extraction` only saves values
of successfully extracted child slots.
Extracting such group slot is equivalent to extracting every child slot
with the `success_only` flag.

Partially extracted group slot is always considered successfully extracted
for the purposes of the `success_only` flag.

## Code explanation

In this example we define two group slots: `person` and `friend`.
Note that in the `person` slot we set `allow_partial_extraction` to `True`
which allows us to _update_ slot values and not
rewrite them in case we don't get full information at once.

So if we send "groot@gmail.com" as user email and after that send only Bitcoin address
the extracted user data would be "<bitcoin_address> groot@gmail.com"
and not "<bitcoin_address> default_email".
We can compare that behaviour with `fried` slot extraction where we have set `success_only=False`
that enables us to send unly partial info that can be overwritten with default values.
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
        allow_partial_extraction=True,
    ),
    "friend": GroupSlot(
        coin_address=RegexpSlot(
            regexp=r"(\b[a-zA-Z0-9]{34}\b)", default_value="default_address"
        ),
        email=RegexpSlot(
            regexp=r"([\w\.-]+@[\w\.-]+\.\w{2,4})",
            default_value="default_email",
        ),
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
            PRE_TRANSITION: {"get_slots": proc.Extract("person")},
            TRANSITIONS: [
                Tr(
                    dst=("root", "utter_user"),
                    cnd=cnd.SlotsExtracted("person.email"),
                    priority=1.2,
                ),
                # Tr(dst=("user_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {RESPONSE: "Please, send your email and bitcoin address."},
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
                Tr(
                    dst=("friend_flow", "ask"),
                    cnd=cnd.ExactMatch("update"),
                    priority=0.8,
                ),
                Tr(dst=("friend_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {
            RESPONSE: "Please, send your friends bitcoin address and email."
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
            RESPONSE: "Your bitcoin address is {person.coin_address}. Your email is {person.email}. You can update your data or type /send to proceed.",
            PRE_RESPONSE: {"fill": proc.FillTemplate()},
            TRANSITIONS: [
                Tr(dst=("friend_flow", "ask"), cnd=cnd.ExactMatch("/send")),
                Tr(dst=("user_flow", "ask")),
            ],
        },
    },
}

HAPPY_PATH = [
    ("Start", "Please, send your email and bitcoin address."),
    (
        "groot@gmail.com",
        "Your bitcoin address is default_address. Your email is groot@gmail.com. You can update your data or type /send to proceed.",
    ),
    ("update", "Please, send your email and bitcoin address."),
    (
        "1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF",
        "Your bitcoin address is 1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF. Your email is groot@gmail.com. You can update your data or type /send to proceed.",
    ),
    ("/send", "Please, send your friends bitcoin address and email."),
    (
        "john_doe@gmail.com",
        "Your friends address is default_address and email is john_doe@gmail.com",
    ),
    ("update", "Please, send your friends bitcoin address and email."),
    (
        "3Nxwenay9Z8Lc9JBiywExpnEFiLp6Afp8v",
        "Your friends address is 3Nxwenay9Z8Lc9JBiywExpnEFiLp6Afp8v and email is default_email",
    ),
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
