import logging
import sys
from typing import List, Tuple, Callable, Optional

from df_engine.core import Context
from df_engine.core.keywords import TRANSITIONS, RESPONSE
import df_engine.conditions as cnd

from df_pipeline import Pipeline

SCRIPT = {
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


TURNS = (
    ("Hi", "Hi, how are you?"),
    ("i'm fine, how are you?", "Good. What do you want to talk about?"),
    ("Let's talk about music.", "Sorry, I can not talk about music now."),
    ("Ok, goodbye.", "bye"),
    ("Hi", "Hi, how are you?"),
)


def get_auto_arg() -> bool:
    return "-a" in sys.argv[1:]


class ConsoleFormatter(logging.Formatter):
    FORMATTERS = {
        logging.DEBUG: logging.Formatter("%(message)s"),
        logging.INFO: logging.Formatter("INFO: %(message)s"),
        "DEFAULT": logging.Formatter("%(name)s - %(levelname)s - %(message)s"),
    }

    def format(self, record):
        formatter = self.FORMATTERS.get(record.levelno, self.FORMATTERS["DEFAULT"])
        return formatter.format(record)


def auto_run_pipeline(
    pipeline: Pipeline,
    turns: List[Tuple[str, str]] = TURNS,
    wrapper: Callable[[str], str] = lambda s: s,
    logger: Optional[logging.Logger] = None,
):
    ctx = Context()
    wrapped_turns = [(request, wrapper(response)) for request, response in turns]

    if logger is not None:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(ConsoleFormatter())
        logger.addHandler(handler)

    for turn_id, (request, true_response) in enumerate(wrapped_turns):
        if logger is not None:
            logger.debug(f"> {request}")
        ctx = pipeline(request, ctx.id)
        if true_response != ctx.last_response:
            msg = f" pipeline={pipeline}"
            msg += f" turn_id={turn_id}"
            msg += f" request={request} "
            msg += f"\ntrue_response != out_response: "
            msg += f"\n{true_response} != {ctx.last_response}"
            raise Exception(msg)
        if logger is not None:
            logger.debug(f"< {ctx.last_response}")
