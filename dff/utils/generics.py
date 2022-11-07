from logging import Logger
from typing import NamedTuple, Optional

from dff.connectors.messenger.generics import Response
from dff.core.engine.core import Context
from dff.core.engine.core.context import get_last_index
from dff.core.pipeline import ServiceBuilder
from dff.utils.common import run_example


class CallbackRequest(NamedTuple):
    payload: str


def process_request(ctx: Context):
    last_request: str = ctx.last_request  # TODO: add _really_ nice ways to modify user request and response
    last_index = get_last_index(ctx.requests)

    ui = ctx.last_response and ctx.last_response.ui
    if ui and ctx.last_response.ui.buttons:
        try:
            chosen_button = ui.buttons[int(last_request)]
        except (IndexError, ValueError):
            raise ValueError("Type in the index of the correct option to choose from the buttons.")
        ctx.requests[last_index] = CallbackRequest(payload=chosen_button.payload)
        return
    ctx.requests[last_index] = last_request


def process_response(ctx: Context):
    last_response: Response = ctx.last_response  # TODO: add _really_ nice ways to modify user request and response
    last_index = get_last_index(ctx.responses)

    ui = last_response.ui
    if ui and ui.buttons:
        options = [f"{str(idx)}): {item.text}" for idx, item in enumerate(ui.buttons)]
        ctx.responses[last_index] = "\n".join(["", last_response.text] + options)
        return

    attachment = last_response.image or last_response.document or last_response.audio or last_response.video
    if attachment and attachment.source:
        with open(attachment.source, "rb") as file:
            bytestr = file.read()
            ctx.responses[last_index] = "\n".join(["", last_response.text, f"Attachment size: {len(bytestr)} bytes."])
            return

    attachments = last_response.attachments
    if attachments:
        size = 0
        for attach in attachments.files:
            with open(attach.source, "rb") as file:
                bytestr = file.read()
                size += len(bytestr)
        ctx.responses[last_index] = "\n".join(["", last_response.text, f"Grouped attachment size: {str(size)} bytes."])
        return

    ctx.responses[last_index] = last_response.text


def run_generics_example(
    logger: Optional[Logger] = None,
    request_wrapper: Optional[ServiceBuilder] = process_request,
    response_wrapper: Optional[ServiceBuilder] = process_response,
    **kwargs
):
    run_example(logger, request_wrapper=request_wrapper, response_wrapper=response_wrapper, **kwargs)
