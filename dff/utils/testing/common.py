from os import getenv
from typing import Callable, Tuple, Any, Optional
from uuid import uuid4

from dff.script import Context, Message
from dff.pipeline import Pipeline
from dff.utils.testing.response_comparers import default_comparer


def is_interactive_mode() -> bool:
    """
    Checking whether the example code should be run in interactive mode.

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
    Running example with provided pipeline for provided requests, comparing responses with correct expected responses.
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
            error_msg = f"\n\npipeline = {pipeline.info_dict}\n\n"
            error_msg += f"ctx = {ctx}\n\n"
            error_msg += f"step_id = {step_id}\n"
            error_msg += f"request = {repr(request)}\n"
            error_msg += f"candidate_response = {repr(parsed_response_with_deviation)}\n"
            error_msg += f"reference_response = {repr(reference_response)}\n"
            error_msg += "candidate_response != reference_response"
            raise Exception(error_msg)


def run_interactive_mode(pipeline: Pipeline):
    """
    Running example with provided pipeline in interactive mode, just like with CLI messenger interface.
    The dialog won't be stored anywhere, it will only be outputted to STDOUT.

    :param pipeline: The Pipeline instance, that will be used for running.
    """

    ctx_id = uuid4()  # Random UID
    print("Start a dialogue with the bot")
    while True:
        request = input(">>> ")
        ctx = pipeline(request=Message(text=request), ctx_id=ctx_id)
        print(f"<<< {repr(ctx.last_response)}")
