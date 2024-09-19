"""
Common
------
This module contains several functions which are used to run demonstrations in tutorials.
"""

from os import getenv
from typing import Tuple, Iterable
from uuid import uuid4

from chatsky.core import Message, Pipeline
from chatsky.core.message import MessageInitTypes


def is_interactive_mode() -> bool:  # pragma: no cover
    """
    Checking whether the tutorial code should be run in interactive mode.

    :return: `True` if it's being executed by Jupyter kernel and DISABLE_INTERACTIVE_MODE env variable isn't set,
        `False` otherwise.
    """

    shell = None
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
    finally:
        return shell != "ZMQInteractiveShell" and getenv("DISABLE_INTERACTIVE_MODE") is None


def check_happy_path(
    pipeline: Pipeline,
    happy_path: Iterable[Tuple[MessageInitTypes, MessageInitTypes]],
    *,
    response_comparator=Message.__eq__,
    printout: bool = False,
):
    """
    Running tutorial with provided pipeline for provided requests, comparing responses with correct expected responses.

    :param pipeline: The Pipeline instance, that will be used for checking.
    :param happy_path: A tuple of (request, response) tuples, so-called happy path,
        its requests are passed to pipeline and the pipeline responses are compared to its responses.
    :param response_comparator:
        Function that checks reference response (first argument) with the actual response (second argument).
        Defaults to ``Message.__eq__``.
    :param printout: Whether to print the requests/responses during iteration.
    """
    ctx_id = uuid4()  # get random ID for current context
    for step_id, (request_raw, reference_response_raw) in enumerate(happy_path):

        request = Message.model_validate(request_raw)
        reference_response = Message.model_validate(reference_response_raw)
        if printout:
            print(f"USER: {request}")

        ctx = pipeline(request, ctx_id)

        actual_response = ctx.last_response
        if printout:
            print(f"BOT : {actual_response}")

        if not response_comparator(reference_response, actual_response):
            raise AssertionError(
                f"""check_happy_path failed
step id: {step_id}
reference response: {reference_response}
actual response: {actual_response}
"""
            )
