from logging import Logger
from os import getenv
from typing import Callable, Tuple, Any
from uuid import uuid4

from dff.core.engine.core import Context
from dff.core.pipeline import Pipeline
from dff.utils.testing.logger import ConsoleFormatter
from dff.utils.testing.response_comparers import default_comparer

logger = Logger(__name__)


def is_interactive_mode() -> bool:
    shell = None
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
    finally:
        return shell != "ZMQInteractiveShell" and getenv("DISABLE_INTERACTIVE_MODE", "False") == "True"


def check_happy_path(
    pipeline: Pipeline,
    happy_path: Tuple[Tuple[Any, Any], ...],
    # This optional argument is used for additional processing of candidate responses and reference responses
    comparer: Callable[[Any, Any, Context], bool] = default_comparer,
):
    ctx_id = uuid4()  # Random UID
    ConsoleFormatter.configure_logger(logger)
    for request, reference_response in happy_path:
        logger.debug(f"USER: {request}")
        ctx = pipeline(request, ctx_id)
        candidate_response = ctx.last_response
        if comparer(candidate_response, reference_response, ctx):
            logger.debug(f"BOT: {request}")
        else:
            raise Exception(f"candidate_response != reference_response: {candidate_response} != {reference_response}")


def run_interactive_mode(pipeline: Pipeline):
    ctx_id = uuid4()  # Random UID
    while True:
        request = input(">>> ")
        ctx = pipeline(request=request, ctx_id=ctx_id)
        print(f"<<< {ctx.last_response}")
