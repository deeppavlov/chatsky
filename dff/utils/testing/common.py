from os import getenv
from typing import Callable, Tuple, Any, Optional
from uuid import uuid4

from dff.core.engine.core import Context
from dff.core.pipeline import Pipeline
from dff.utils.testing.response_comparers import default_diff


def is_interactive_mode() -> bool:
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
    candidate_response_diff: Callable[[Any, Any, Context], Optional[str]] = default_diff,
    printout_enable: bool = True,
):
    ctx_id = uuid4()  # get random ID for current context
    for step_id, (request, reference_response) in enumerate(happy_path):
        ctx = pipeline(request, ctx_id)
        candidate_response = ctx.last_response
        if printout_enable:
            print(f"(user) >>> {request}")
            print(f" (bot) <<< {candidate_response}")
        transformed_candidate_response = candidate_response_diff(candidate_response, reference_response, ctx)
        if transformed_candidate_response is not None:
            error_msg = f"\n\npipeline = {pipeline.info_dict}\n\n"
            error_msg += f"ctx = {ctx}\n\n"
            error_msg += f"step_id = {step_id}\n"
            error_msg += f"request = {request}\n"
            error_msg += f"candidate_response = {transformed_candidate_response}\n"
            error_msg += f"reference_response = {reference_response}\n"
            error_msg += "candidate_response != reference_response"
            raise Exception(error_msg)


def run_interactive_mode(pipeline: Pipeline):
    ctx_id = uuid4()  # Random UID
    print("Start a dialogue with the bot")
    while True:
        request = input(">>> ")
        ctx = pipeline(request=request, ctx_id=ctx_id)
        print(f"<<< {ctx.last_response}")
