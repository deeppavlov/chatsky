"""
Common
------
This module contains several functions which are used to run demonstrations in tutorials.
"""
from os import getenv
from typing import Callable, Tuple, Any, Optional
from uuid import uuid4

from dff.script import Context, Message
from dff.pipeline import Pipeline
from dff.utils.testing.response_comparers import default_comparer


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
    happy_path: Tuple[Tuple[Any, Any], ...],
    # This optional argument is used for additional processing of candidate responses and reference responses
    response_comparer: Callable[[Any, Any, Context], Optional[str]] = default_comparer,
    printout_enable: bool = True,
):
    """
    Running tutorial with provided pipeline for provided requests, comparing responses with correct expected responses.
    In cases when additional processing of responses is needed (e.g. in case of response being an HTML string),
    a special function (response comparer) is used.

    :param pipeline: The Pipeline instance, that will be used for checking.
    :param happy_path: A tuple of (request, response) tuples, so-called happy path,
        its requests are passed to pipeline and the pipeline responses are compared to its responses.
    :param response_comparer: A special comparer function that accepts received response, true response and context;
        it returns `None` is two responses are equal and transformed received response if they are different.
    :param printout_enable: A flag that enables requests and responses fancy printing (to STDOUT).
    """

    ctx_id = uuid4()  # get random ID for current context
    for step_id, (request, reference_response) in enumerate(happy_path):
        ctx = pipeline(request, ctx_id)
        candidate_response = ctx.last_response
        if printout_enable:
            print(f"(user) >>> {repr(request)}")
            print(f" (bot) <<< {repr(candidate_response)}")
        parsed_response_with_deviation = response_comparer(candidate_response, reference_response, ctx)
        if parsed_response_with_deviation is not None:
            raise Exception(
                f"\n\npipeline = {pipeline.info_dict}\n\n"
                f"ctx = {ctx}\n\n"
                f"step_id = {step_id}\n"
                f"request = {repr(request)}\n"
                f"candidate_response = {repr(parsed_response_with_deviation)}\n"
                f"reference_response = {repr(reference_response)}\n"
                "candidate_response != reference_response"
            )


def run_interactive_mode(pipeline: Pipeline):  # pragma: no cover
    """
    Running tutorial with provided pipeline in interactive mode, just like with CLI messenger interface.
    The dialog won't be stored anywhere, it will only be outputted to STDOUT.

    :param pipeline: The Pipeline instance, that will be used for running.
    """

    ctx_id = uuid4()  # Random UID
    print("Start a dialogue with the bot")
    while True:
        request = input(">>> ")
        ctx = pipeline(request=Message(text=request), ctx_id=ctx_id)
        print(f"<<< {repr(ctx.last_response)}")
