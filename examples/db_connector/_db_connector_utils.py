"""
1. Utils
========
"""

import logging
import random
import sys
from typing import Optional

from dff.core.engine import conditions as cnd
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import RESPONSE, TRANSITIONS

from dff.connectors.db import DBConnector
from examples.utils import ConsoleFormatter

script = {
    "greeting_flow": {
        "start_node": {  # This is an initial node, it doesn't need a `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},  # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: "Hi, what is up?",
            TRANSITIONS: {"node2": cnd.exact_match("alright")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": cnd.exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about that now.",
            TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")},
        },
        "node4": {RESPONSE: "bye", TRANSITIONS: {"node1": cnd.exact_match("Hi")}},
        "fallback_node": {  # We get to this node if an error occurred while the agent was running
            RESPONSE: "Oops",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
    }
}

testing_dialog = [
    ("Hi", "Hi, what is up?"),  # start_node -> node1
    ("alright", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about that now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
    ("Hi", "Hi, what is up?"),  # node4 -> node1
    ("stop", "Ooops"),  # node1 -> fallback_node
    ("stop", "Ooops"),  # fallback_node -> fallback_node
    ("Hi", "Hi, what is up?"),  # fallback_node -> node1
    ("alright", "Good. What do you want to talk about?"),  # node1 -> node2
    ("Let's talk about music.", "Sorry, I can not talk about that now."),  # node2 -> node3
    ("Ok, goodbye.", "bye"),  # node3 -> node4
]


def run_actor(
    in_request: str,
    actor: Actor,
    db: DBConnector,
    logger: logging.Logger,
    user_id: str,
    true_out_response: Optional[str] = None
):
    if logger is not None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(ConsoleFormatter())
        logger.addHandler(handler)
        logger.debug(f"USER: {in_request}")

    ctx = db.get(user_id, Context(id=user_id))
    ctx.add_request(in_request)
    ctx = actor(ctx)
    out_response = ctx.last_response
    db[user_id] = ctx
    logger.info(f"in_request={in_request} -> {out_response}")

    if true_out_response is not None and true_out_response != out_response:
        msg = f"in_request={in_request} -> true_out_response != out_response: {true_out_response} != {out_response}"
        raise Exception(msg)
    elif logger is not None:
        logger.debug(f"BOT: {out_response}")
    else:
        print(f"<<< {out_response}")

    return out_response, ctx


def run_auto_mode(
    actor: Actor,
    db_connector: DBConnector,
    logger: Optional[logging.Logger] = None,
    user_id=str(random.randint(0, 100))
):
    for in_request, true_out_response in testing_dialog:
        _, ctx = run_actor(in_request, actor, db_connector, logger, user_id, true_out_response)


def run_interactive_mode(
    actor: Actor,
    db_connector: DBConnector,
    logger: Optional[logging.Logger] = None,
    user_id=str(random.randint(0, 100))
):
    while True:
        in_request = input(">>> ")
        _, ctx = run_actor(in_request, actor, db_connector, logger, user_id, None)

