import logging
import random
from typing import Optional

from df_engine import responses as rsp
from df_engine import conditions as cnd
from df_engine.core import Context, Actor
from df_engine.core.keywords import RESPONSE, TRANSITIONS

from df_db_connector import connector_factory

logger = logging.getLogger(__name__)

script = {
    "greeting_flow": {
        "start_node": {  # This is an initial node, it doesn't need a `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},  # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: rsp.choice(["Hi, what is up?", "Hello, how are you?"]),  # random choice from candicate list
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

connector = connector_factory("json://file.json")
# You can import any other connector using this factory:
# connector = connector_factory("pickle://file.pkl")
# connector = connector_factory("shelve://file")

USER_ID = str(random.randint(0, 100))

# The function interacts with a global connector object
def turn_handler(in_request: str, actor: Actor, true_out_response: Optional[str] = None):
    ctx = connector.get(USER_ID, Context(id=USER_ID))
    ctx.add_request(in_request)
    ctx = actor(ctx)
    out_response = ctx.last_response
    connector[USER_ID] = ctx

    if true_out_response is not None and true_out_response != out_response:
        msg = f"in_request={in_request} -> true_out_response != out_response: {true_out_response} != {out_response}"
        raise Exception(msg)
    else:
        logging.info(f"in_request={in_request} -> {out_response}")
    return out_response, ctx


def main(actor):
    while True:
        in_request = input("type your answer: ")
        turn_handler(in_request, actor)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s", level=logging.INFO
    )
    main(actor)
