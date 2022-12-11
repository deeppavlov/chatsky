from typing import NamedTuple

import dff.script.conditions as cnd
import dff.script.labels as lbl
from dff.script import Context, Actor, get_last_index, TRANSITIONS, RESPONSE

from dff.script.responses import Button, Keyboard, Response
from dff.pipeline import Pipeline
from dff.utils.testing import check_happy_path, is_interactive_mode, run_interactive_mode, generics_comparer


def check_button_payload(value: str):
    def payload_check_inner(ctx: Context, actor: Actor):
        return hasattr(ctx.last_request, "payload") and ctx.last_request.payload == value

    return payload_check_inner


toy_script = {
    "root": {
        "start": {
            RESPONSE: Response(text=""),
            TRANSITIONS: {
                ("general", "question_1"): cnd.true(),
            },
        },
        "fallback": {RESPONSE: Response(text="Finishing test")},
    },
    "general": {
        "question_1": {
            RESPONSE: Response(
                **{
                    "text": "Starting test! What's 2 + 2? (type in the index of the correct option)",
                    "ui": Keyboard(
                        buttons=[
                            Button(text="5", payload="5"),
                            Button(text="4", payload="4"),
                        ]
                    ),
                }
            ),
            TRANSITIONS: {
                lbl.forward(): check_button_payload("4"),
                ("general", "question_1"): check_button_payload("5"),
            },
        },
        "question_2": {
            RESPONSE: Response(
                **{
                    "text": "Next question: what's 6 * 8? (type in the index of the correct option)",
                    "ui": Keyboard(
                        buttons=[
                            Button(text="38", payload="38"),
                            Button(text="48", payload="48"),
                        ]
                    ),
                }
            ),
            TRANSITIONS: {
                lbl.forward(): check_button_payload("48"),
                ("general", "question_2"): check_button_payload("38"),
            },
        },
        "question_3": {
            RESPONSE: Response(
                **{
                    "text": "What's 114 + 115? (type in the index of the correct option)",
                    "ui": Keyboard(
                        buttons=[
                            Button(text="229", payload="229"),
                            Button(text="283", payload="283"),
                        ]
                    ),
                }
            ),
            TRANSITIONS: {
                lbl.forward(): check_button_payload("229"),
                ("general", "question_3"): check_button_payload("283"),
            },
        },
        "success": {
            RESPONSE: Response(text="Success!"),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
    },
}


happy_path = (
    ("Hi", "\nStarting test! What's 2 + 2? (type in the index of the correct option)\n0): 5\n1): 4"),
    ("0", "\nStarting test! What's 2 + 2? (type in the index of the correct option)\n0): 5\n1): 4"),
    ("1", "\nNext question: what's 6 * 8? (type in the index of the correct option)\n0): 38\n1): 48"),
    ("0", "\nNext question: what's 6 * 8? (type in the index of the correct option)\n0): 38\n1): 48"),
    ("1", "\nWhat's 114 + 115? (type in the index of the correct option)\n0): 229\n1): 283"),
    ("1", "\nWhat's 114 + 115? (type in the index of the correct option)\n0): 229\n1): 283"),
    ("0", "Success!"),
    ("ok", "Finishing test"),
)


class CallbackRequest(NamedTuple):
    payload: str


def process_request(ctx: Context):
    last_request: str = ctx.last_request  # TODO: add _really_ nice ways to modify user request and response
    last_index = get_last_index(ctx.requests)

    ui = ctx.last_response and ctx.last_response.ui
    if ui and ctx.last_response.ui.buttons:
        try:
            chosen_button = ui.buttons[int(last_request)]
        except (IndexError, ValueError):
            raise ValueError("Type in the index of the correct option to choose from the buttons.")
        ctx.requests[last_index] = CallbackRequest(payload=chosen_button.payload)
        return
    ctx.requests[last_index] = last_request


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
        generics_comparer,
    )  # For response object with `happy_path` string comparing, a special `generics_comparer` comparator is used
    if is_interactive_mode():
        run_interactive_mode(pipeline)
