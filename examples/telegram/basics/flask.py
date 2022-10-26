import os

import dff.core.engine.conditions as cnd
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from dff.core.runner import ScriptRunner

from dff.connectors.messenger.telegram.request_provider import FlaskRequestProvider
from dff.connectors.messenger.telegram.connector import TelegramConnector

from flask import Flask

app = Flask(__name__)

script = {
    "greeting_flow": {
        "start_node": {  # This is an initial node, it doesn't need an `RESPONSE`
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},  # If "Hi" == request of user then we make the transition
        },
        "node1": {
            RESPONSE: "Hi, how are you?",  # When the agent goes to node1, we return "Hi, how are you?"
            TRANSITIONS: {"node2": cnd.regexp(r".*(good|fine|great).*")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": cnd.regexp(r"(music[.!]{0,1}|.*about music[.!]{0,1})")},
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")},
        },
        "node4": {RESPONSE: "bye", TRANSITIONS: {"node1": cnd.regexp(r".*(restart|start|start again).*")}},
        "fallback_node": {  # We get to this node if an error occurred while the agent was running
            RESPONSE: "Ooops",
            TRANSITIONS: {"node1": cnd.true()},
        },
    }
}

bot = TelegramConnector(os.getenv("BOT_TOKEN", "SOMETOKEN"))

provider = FlaskRequestProvider(bot=bot, app=app)

runner = ScriptRunner(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    db=dict(),
    request_provider=provider,
)

if __name__ == "__main__":
    runner.start()
