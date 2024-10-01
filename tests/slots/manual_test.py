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
import logging
logging.basicConfig(level=logging.DEBUG)

from chatsky.utils.testing import (
    check_happy_path,
    is_interactive_mode,
)

SLOTS = {
    "person": GroupSlot(
        username=RegexpSlot(
            regexp=r"username is ([a-zA-Z]+)",
            match_group_idx=1,
        ),
        email=RegexpSlot(
            regexp=r"email is ([a-z@\.A-Z]+)",
            match_group_idx=1,
        )
    ),
    "friend": GroupSlot(
        first_name=RegexpSlot(regexp=r"^[A-Z][a-z]+?(?= )", default_value="default_name"),
        last_name=RegexpSlot(regexp=r"(?<= )[A-Z][a-z]+", default_value="default_surname"),
        allow_partially_extracted=True
    )
}

script = {
    GLOBAL: {
        TRANSITIONS: [
            Tr(dst=("username_flow", "ask"), cnd=cnd.Regexp(r"^[sS]tart"))
        ]
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
            PRE_TRANSITION: {"get_slots": proc.Extract("friend", success_only=False)},
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
