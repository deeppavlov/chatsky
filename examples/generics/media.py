#!/usr/bin/env python3
import logging

from df_engine.core.keywords import RESPONSE, TRANSITIONS
from df_engine.core import Context, Actor
from df_engine import conditions as cnd

from df_generics.response import Attachments, Image, Response
from .example_utils import run_test, run_interactive_mode

script = {
    "root": {
        "start": {
            RESPONSE: Response(text=""),
            TRANSITIONS: {("pics", "ask_picture"): cnd.true()},
        },
        "fallback": {
            RESPONSE: Response(text="Final node reached, send any message to restart."),
            TRANSITIONS: {("pics", "ask_picture"): cnd.true()},
        },
    },
    "pics": {
        "ask_picture": {
            RESPONSE: Response(text="Please, send me a picture url"),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.regexp(r"^http.+\.png$"),
                ("pics", "send_many", 1.0): cnd.regexp(r"^http.+\.jpg$"),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
        "send_one": {
            RESPONSE: Response(text="here's my picture!", image=Image(source="examples/kitten.jpg")),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "send_many": {
            RESPONSE: Response(
                text="Look at my pictures",
                attachments=Attachments(files=[Image(source="examples/kitten.jpg")] * 10),
            ),
            TRANSITIONS: {("root", "fallback"): cnd.true()},
        },
        "repeat": {
            RESPONSE: Response(text="I cannot find the picture. Please, try again."),
            TRANSITIONS: {
                ("pics", "send_one", 1.1): cnd.regexp(r"^http.+\.png$"),
                ("pics", "send_many", 1.0): cnd.regexp(r"^http.+\.jpg$"),
                ("pics", "repeat", 0.9): cnd.true(),
            },
        },
    },
}

actor = Actor(script=script, start_label=("root", "start"), fallback_label=("root", "fallback"))

testing_dialog = [
    ("Hi", "Please, send me a picture url"),
    ("no", "I cannot find the picture. Please, try again."),
    ("https://sun9-49.userapi.com/s/v1/if2/gpquN.png", "\nhere's my picture!\nAttachment size: 36643 bytes."),
    ("ok", "Final node reached, send any message to restart."),
    ("ok", "Please, send me a picture url"),
    ("https://sun9-49.userapi.com/s/v1/if2/gpquN.jpg", "\nLook at my pictures\nGrouped attachment size: 366430 bytes."),
    ("ok", "Final node reached, send any message to restart."),
]

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s",
        level=logging.INFO,
    )
    # run_test()
    run_interactive_mode(actor)
