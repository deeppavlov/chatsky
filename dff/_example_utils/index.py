import sys
from logging import Logger, StreamHandler, DEBUG, Formatter, INFO
from typing import List, Tuple, Callable, Optional, Any, Union

from dff.core.engine.conditions import exact_match
from dff.core.engine.core import Context, Actor
from dff.core.engine.core.keywords import RESPONSE, TRANSITIONS
from dff.core.pipeline import Pipeline

SCRIPT = {
    "greeting_flow": {
        "start_node": {
            RESPONSE: "",
            TRANSITIONS: {"node1": exact_match("Hi")},
        },
        "node1": {
            RESPONSE: "Hi, how are you?",
            TRANSITIONS: {"node2": exact_match("i'm fine, how are you?")},
        },
        "node2": {
            RESPONSE: "Good. What do you want to talk about?",
            TRANSITIONS: {"node3": exact_match("Let's talk about music.")},
        },
        "node3": {
            RESPONSE: "Sorry, I can not talk about music now.",
            TRANSITIONS: {"node4": exact_match("Ok, goodbye.")},
        },
        "node4": {
            RESPONSE: "bye",
            TRANSITIONS: {"node1": exact_match("Hi")}
        },
        "fallback_node": {
            RESPONSE: "Ooops",
            TRANSITIONS: {"node1": exact_match("Hi")},
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


def is_in_notebook() -> bool:
    shell = None
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
    finally:
        return shell == "ZMQInteractiveShell"


class ConsoleFormatter(Formatter):
    FORMATTERS = {
        DEBUG: Formatter("%(message)s"),
        INFO: Formatter("INFO: %(message)s"),
        "DEFAULT": Formatter("%(name)s - %(levelname)s - %(message)s"),
    }

    def format(self, record):
        formatter = self.FORMATTERS.get(record.levelno, self.FORMATTERS["DEFAULT"])
        return formatter.format(record)

    @staticmethod
    def set_logger(logger: Optional[Logger]):
        if logger is not None:
            handler = StreamHandler(sys.stdout)
            handler.setLevel(DEBUG)
            handler.setFormatter(ConsoleFormatter())
            logger.addHandler(handler)

    @staticmethod
    def log_request(logger: Logger, request: str, auto: bool = False):
        if logger is not None:
            logger.debug(f"USER: {request}")
        elif auto:
            print(f">>> {request}")

    @staticmethod
    def log_response(logger: Logger, response: str):
        if logger is not None:
            logger.debug(f"BOT: {response}")
        else:
            print(f"<<< {response}")


def run_pipeline(
    pipeline: Pipeline,
    turns: List[Tuple[Any, Any]] = TURNS,
    request_wrapper: Callable[[str, Context], str] = lambda s, _: s,
    response_wrapper: Callable[[str, Context], str] = lambda s, _: s,
    logger: Optional[Logger] = None,
):
    ctx = Context()
    wrapped_turns = [(request_wrapper(request, ctx), response_wrapper(response, ctx)) for request, response in turns]
    ConsoleFormatter.set_logger(logger)

    for turn_id, (request, true_response) in enumerate(wrapped_turns):
        ConsoleFormatter.log_request(logger, request, True)
        ctx = pipeline(request, ctx.id)
        if true_response != ctx.last_response:
            msg = f" pipeline={pipeline}"
            msg += f" turn_id={turn_id}"
            msg += f" request={request} "
            msg += "\ntrue_response != out_response: "
            msg += f"\n{true_response} != {ctx.last_response}"
            raise Exception(msg)
        ConsoleFormatter.log_response(logger, ctx.last_response)


def run_actor(
    request: Any,
    ctx: Union[Context, str, dict],
    actor: Actor,
    true_response: Optional[str] = None,
    request_wrapper: Callable[[Any, Context], str] = lambda s, _: s,
    response_wrapper: Callable[[Any, Context], str] = lambda s, _: s,
    logger: Optional[Logger] = None,
):
    ConsoleFormatter.log_request(logger, request)
    ctx = Context.cast(ctx)
    ctx.add_request(request_wrapper(request, ctx))
    ctx = actor(ctx)
    actual_response = response_wrapper(ctx.last_response, ctx)
    if true_response is not None and true_response != actual_response:
        msg = f"in_request={request} -> true_response != actual_response: {true_response} != {actual_response}"
        raise Exception(msg)
    ConsoleFormatter.log_response(logger, actual_response)
    return actual_response, ctx


def run_auto_mode(
    actor: Actor,
    testing_dialog: List[Tuple[Any, Any]] = TURNS,
    logger: Optional[Logger] = None
):
    ctx = {}
    ConsoleFormatter.set_logger(logger)
    for in_request, true_response in testing_dialog:
        _, ctx = run_actor(in_request, ctx, actor, true_response, logger=logger)


def run_interactive_mode(
    actor: Actor,
    logger: Optional[Logger] = None
):
    ctx = {}
    ConsoleFormatter.set_logger(logger)
    while True:
        in_request = input(">>> ")
        _, ctx = run_actor(in_request, ctx, actor, logger=logger)
