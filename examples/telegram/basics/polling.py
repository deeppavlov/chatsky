import logging
import os

import dff.core.engine.conditions as cnd
from dff.core.engine.core.keywords import TRANSITIONS, RESPONSE

from dff.connectors.messenger.telegram.connector import DFFTeleBot
from dff.connectors.messenger.telegram.interface import PollingTelegramInterface
from dff.core.pipeline import Pipeline

from examples.telegram._telegram_utils import check_env_bot_tokens, get_auto_arg, auto_run_pipeline

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

script = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: "",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
        "node1": {
            RESPONSE: "Hi, how are you?",
            TRANSITIONS: {"node2": cnd.exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": cnd.exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: {"node4": cnd.exact_match("Ok, goodbye.")},
        },
        "node4": {RESPONSE: "bye", TRANSITIONS: {"node1": cnd.exact_match("Hi")}},
        "fallback_node": {
            RESPONSE: "Ooops",
            TRANSITIONS: {"node1": cnd.exact_match("Hi")},
        },
    }
}

bot = DFFTeleBot(os.getenv("BOT_TOKEN", "SOMETOKEN"))

interface = PollingTelegramInterface(bot=bot)

pipeline = Pipeline.from_script(
    script=script,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
    context_storage=dict(),
    messenger_interface=interface,
)

if __name__ == "__main__":
    check_env_bot_tokens()
    if get_auto_arg():
        auto_run_pipeline(pipeline, logger=logger)
    else:
        pipeline.run()
