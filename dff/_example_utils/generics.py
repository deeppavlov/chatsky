from logging import Logger
from typing import NamedTuple, List, Tuple, Any, Optional

from dff.connectors.messenger.generics import Response
from dff.core.engine.core import Actor, Context

from .index import TURNS, ConsoleFormatter, run_actor


class CallbackRequest(NamedTuple):
    payload: str


def process_request(request: str, ctx: Context):
    ui = ctx.last_response and ctx.last_response.ui
    if ui and ctx.last_response.ui.buttons:
        try:
            chosen_button = ui.buttons[int(request)]
        except (IndexError, ValueError):
            raise ValueError("Type in the index of the correct option to choose from the buttons.")
        return CallbackRequest(payload=chosen_button.payload)
    return request


def process_response(response: Response, _: Context) -> str:
    ui = response.ui
    if ui and ui.buttons:
        options = [f"{str(idx)}): {item.text}" for idx, item in enumerate(ui.buttons)]
        return "\n".join(["", response.text] + options)

    attachment = response.image or response.document or response.audio or response.video
    if attachment and attachment.source:
        with open(attachment.source, "rb") as file:
            bytestr = file.read()
            return "\n".join(["", response.text, f"Attachment size: {len(bytestr)} bytes."])

    attachments = response.attachments
    if attachments:
        size = 0
        for attach in attachments.files:
            with open(attach.source, "rb") as file:
                bytestr = file.read()
                size += len(bytestr)
        return "\n".join(["", response.text, f"Grouped attachment size: {str(size)} bytes."])

    return response.text


def run_auto_mode(actor: Actor, testing_dialog: List[Tuple[Any, Any]] = TURNS, logger: Optional[Logger] = None):
    ctx = {}
    ConsoleFormatter.set_logger(logger)
    for in_request, true_response in testing_dialog:
        _, ctx = run_actor(
            in_request,
            ctx,
            actor,
            true_response,
            request_wrapper=process_request,
            response_wrapper=process_response,
            logger=logger,
        )


def run_interactive_mode(actor: Actor, logger: Optional[Logger] = None):
    ctx = {}
    ConsoleFormatter.set_logger(logger)
    while True:
        in_request = input(">>> ")
        _, ctx = run_actor(
            in_request, ctx, actor, request_wrapper=process_request, response_wrapper=process_response, logger=logger
        )
