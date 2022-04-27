#!/usr/bin/env python3
import re
from typing import Optional
import logging

import df_engine.conditions as cnd
import df_engine.labels as lbl
from df_engine.core import Context, Actor
from df_engine.core.keywords import TRANSITIONS, RESPONSE

from df_generics.response import Button, Keyboard, Response
from .example_utils import run_test, run_interactive_mode


def check_button_payload(value: str):
    def payload_check_inner(ctx: Context, actor: Actor):
        return hasattr(ctx.last_request, "payload") and ctx.last_request.payload == value

    return payload_check_inner


script = {
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


testing_dialog = [
    ("Hi", "\nStarting test! What's 2 + 2? (type in the index of the correct option)\n0): 5\n1): 4"),
    ("0", "\nStarting test! What's 2 + 2? (type in the index of the correct option)\n0): 5\n1): 4"),
    ("1", "\nNext question: what's 6 * 8? (type in the index of the correct option)\n0): 38\n1): 48"),
    ("0", "\nNext question: what's 6 * 8? (type in the index of the correct option)\n0): 38\n1): 48"),
    ("1", "\nWhat's 114 + 115? (type in the index of the correct option)\n0): 229\n1): 283"),
    ("1", "\nWhat's 114 + 115? (type in the index of the correct option)\n0): 229\n1): 283"),
    ("0", "Success!"),
    ("ok", "Finishing test"),
]

actor = Actor(script=script, start_label=("root", "start"), fallback_label=("root", "fallback"))

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    # run_test()
    run_interactive_mode(actor)
