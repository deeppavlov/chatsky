# %% [markdown]
"""
# Responses: 2. Buttons

In this tutorial %mddoclink(api,script.core.message,Button)
class is demonstrated.
Buttons are one of %mddoclink(api,script.core.message,Message) fields.
They can be attached to any message but will only work if the chosen
[messenger interface](%doclink(api,index_messenger_interfaces)) supports them.
"""


# %pip install dff

# %%
import dff.script.conditions as cnd
import dff.script.labels as lbl
from dff.script import Context, TRANSITIONS, RESPONSE

from dff.script.core.message import Button, Keyboard, Message
from dff.pipeline import Pipeline
from dff.utils.testing import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)


# %%
def check_button_payload(value: str):
    def payload_check_inner(ctx: Context, _: Pipeline):
        if ctx.last_request.misc is not None:
            return ctx.last_request.misc.get("payload") == value
        else:
            return False

    return payload_check_inner


# %%
toy_script = {
    "root": {
        "start": {
            RESPONSE: Message(""),
            TRANSITIONS: {
                ("general", "question_1"): cnd.true(),
            },
        },
        "fallback": {RESPONSE: Message("Finishing test")},
    },
    "general": {
        "question_1": {
            RESPONSE: Message(
                **{
                    "text": "Starting test! What's 2 + 2?"
                    " (type in the index of the correct option)",
                    "misc": {
                        "ui": Keyboard(
                            buttons=[
                                Button(text="5", payload="5"),
                                Button(text="4", payload="4"),
                            ]
                        ),
                    },
                }
            ),
            TRANSITIONS: {
                lbl.forward(): check_button_payload("4"),
                ("general", "question_1"): check_button_payload("5"),
            },
        },
        "question_2": {
            RESPONSE: Message(
                **{
                    "text": "Next question: what's 6 * 8?"
                    " (type in the index of the correct option)",
                    "misc": {
                        "ui": Keyboard(
                            buttons=[
                                Button(text="38", payload="38"),
                                Button(text="48", payload="48"),
                            ]
                        ),
                    },
                }
            ),
            TRANSITIONS: {
                lbl.forward(): check_button_payload("48"),
                ("general", "question_2"): check_button_payload("38"),
            },
        },
        "question_3": {
            RESPONSE: Message(
                **{
                    "text": "What's 114 + 115? "
                    "(type in the index of the correct option)",
                    "misc": {
                        "ui": Keyboard(
                            buttons=[
                                Button(text="229", payload="229"),
                                Button(text="283", payload="283"),
                            ]
                        ),
                    },
                }
            ),
            TRANSITIONS: {
                lbl.forward(): check_button_payload("229"),
                ("general", "question_3"): check_button_payload("283"),
            },
        },
        "success": {
            RESPONSE: Message("Success!"),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}

happy_path = (
    (
        Message("Hi"),
        Message(
            **{
                "text": "Starting test! What's 2 + 2? "
                "(type in the index of the correct option)",
                "misc": {
                    "ui": Keyboard(
                        buttons=[
                            Button(text="5", payload="5"),
                            Button(text="4", payload="4"),
                        ]
                    )
                },
            }
        ),
    ),
    (
        Message("0"),
        Message(
            **{
                "text": "Starting test! What's 2 + 2? "
                "(type in the index of the correct option)",
                "misc": {
                    "ui": Keyboard(
                        buttons=[
                            Button(text="5", payload="5"),
                            Button(text="4", payload="4"),
                        ]
                    ),
                },
            }
        ),
    ),
    (
        Message("1"),
        Message(
            **{
                "text": "Next question: what's 6 * 8? "
                "(type in the index of the correct option)",
                "misc": {
                    "ui": Keyboard(
                        buttons=[
                            Button(text="38", payload="38"),
                            Button(text="48", payload="48"),
                        ]
                    ),
                },
            }
        ),
    ),
    (
        Message("0"),
        Message(
            **{
                "text": "Next question: what's 6 * 8? "
                "(type in the index of the correct option)",
                "misc": {
                    "ui": Keyboard(
                        buttons=[
                            Button(text="38", payload="38"),
                            Button(text="48", payload="48"),
                        ]
                    ),
                },
            }
        ),
    ),
    (
        Message("1"),
        Message(
            **{
                "text": "What's 114 + 115? "
                "(type in the index of the correct option)",
                "misc": {
                    "ui": Keyboard(
                        buttons=[
                            Button(text="229", payload="229"),
                            Button(text="283", payload="283"),
                        ]
                    ),
                },
            }
        ),
    ),
    (
        Message("1"),
        Message(
            **{
                "text": "What's 114 + 115? "
                "(type in the index of the correct option)",
                "misc": {
                    "ui": Keyboard(
                        buttons=[
                            Button(text="229", payload="229"),
                            Button(text="283", payload="283"),
                        ]
                    ),
                },
            }
        ),
    ),
    (Message("0"), Message("Success!")),
    (Message("ok"), Message("Finishing test")),
)


def process_request(ctx: Context):
    ui = (
        ctx.last_response
        and ctx.last_response.misc
        and ctx.last_response.misc.get("ui")
    )
    if ui and ui.buttons:
        try:
            chosen_button = ui.buttons[int(ctx.last_request.text)]
        except (IndexError, ValueError):
            raise ValueError(
                "Type in the index of the correct option "
                "to choose from the buttons."
            )
        ctx.last_request = Message(misc={"payload": chosen_button.payload})


# %%
pipeline = Pipeline.from_script(
    toy_script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    pre_services=[process_request],
)

if __name__ == "__main__":
    check_happy_path(
        pipeline,
        happy_path,
    )  # For response object with `happy_path` string comparing,
    # a special `generics_comparer` comparator is used
    if is_interactive_mode():
        run_interactive_mode(pipeline)
