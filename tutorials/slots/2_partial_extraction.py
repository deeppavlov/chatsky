# %% [markdown]
"""
# 2. Partial slot extraction

This tutorial will show more advanced way of using slots by utilizing `GroupSlot` and different parameters it provides us with.
By using Group slots you can extract multiple slots at once if they are placed in one group.
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
In this example we define two group slots for `person` and for a `friend`. Note, that in `friend` slot we set a flag `allow_partially_extracted` to `True` that allows us to _update_ slot values and not totally rewrite them in case we did not get full information first time.

So in this example if we send "John Doe" as a friends name and after that send only name e.g. "Mike" the last extracted friends name would be "Mike Doe" and not "Mike default_surname".

Another feature is `success_only` flag in `Extract` function that ensures that group slot will be extracted if ALL of the slots in it were extracted successfully.
"""

# %%
SLOTS = {
    "person": GroupSlot(
        username=RegexpSlot(
            regexp=r"([a-zA-Z]+)",
            match_group_idx=1,
        ),
        email=RegexpSlot(
            regexp=r"([a-z@\.A-Z]+)",
            match_group_idx=1,
        ),
    ),
    "friend": GroupSlot(
        first_name=RegexpSlot(regexp=r"^[A-Z][a-z]+?(?= )", default_value="default_name"),
        last_name=RegexpSlot(regexp=r"(?<= )[A-Z][a-z]+", default_value="default_surname"),
        allow_partially_extracted=True,
    )
}

script = {
    GLOBAL: {TRANSITIONS: [Tr(dst=("user_flow", "ask"), cnd=cnd.Regexp(r"^[sS]tart"))]},
    "user_flow": {
        LOCAL: {
            PRE_TRANSITION: {"get_slots": proc.Extract("person", success_only=True)},
            TRANSITIONS: [
                Tr(
                    dst=("root", "utter_user"),
                    cnd=cnd.SlotsExtracted("person", mode="any"),
                    priority=1.2,
                ),
                Tr(dst=("user_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {RESPONSE: "Please, send your username and email in one message."},
        "repeat_question": {RESPONSE: "Please, send your username and email again."},
    },
    "friend_flow": {
        LOCAL: {
            PRE_TRANSITION: {"get_slots": proc.Extract("friend", success_only=False)},
            TRANSITIONS: [
                Tr(
                    dst=("root", "utter_friends"),
                    cnd=cnd.SlotsExtracted("friend.first_name", "friend.last_name", mode="any"),
                    priority=1.2,
                ),
                Tr(dst=("friend_flow", "repeat_question"), priority=0.8),
            ],
        },
        "ask": {RESPONSE: "Please, send your friends name"},
        "repeat_question": {RESPONSE: "Please, send your friends name again."},
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
            RESPONSE: rsp.FilledTemplate("Your friend is {friend.first_name} {friend.last_name}"),
            TRANSITIONS: [Tr(dst=("friend_flow", "ask"))],
        },
        "utter_user": {
            RESPONSE: "Your username is {person.username}. " "Your email is {person.email}.",
            PRE_RESPONSE: {"fill": proc.FillTemplate()},
            TRANSITIONS: [Tr(dst=("root", "utter_friend"))]
        },
    },
}

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
    (
        "again",
        "Please, name me one of your friends: (John Doe)",
    ),
    ("Jim ", "Your friend is Jim Page")
]

# %%
pipeline = Pipeline(
    script=script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    slots=SLOTS,
)
