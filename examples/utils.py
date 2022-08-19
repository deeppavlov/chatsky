import logging
import random

from df_engine import conditions as cnd
from df_engine.core import Context, Actor
from df_engine.core.keywords import RESPONSE, TRANSITIONS

from df_db_connector import DBConnector

logger = logging.getLogger(__name__)

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

actor = Actor(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))


def run_actor(in_request: str, actor: Actor, db: DBConnector, user_id=str(random.randint(0, 100))):
    ctx = db.get(user_id, Context(id=user_id))
    ctx.add_request(in_request)
    ctx = actor(ctx)
    out_response = ctx.last_response
    db[user_id] = ctx
    logger.info(f"in_request={in_request} -> {out_response}")
    return out_response, ctx
