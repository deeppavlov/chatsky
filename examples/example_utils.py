"""
This module aims to emulate user interaction with text-based interface and button-based interface

| Instead of clicking the button, the user is promted to enter the button index.

| The media is processed by printing the size of the byte array in the command line interface
| instead of rendering the media file itself.

"""
import logging
from typing import Union, Optional, NamedTuple

from df_engine.core import Context, Actor
from df_generics import Response, Keyboard


class CallbackRequest(NamedTuple):
    payload: str


def process_response(response: Response) -> str:
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


def process_request(ctx: Context, request: str):
    ui = ctx.last_response and ctx.last_response.ui
    if ui and ctx.last_response.ui.buttons:
        try:
            chosen_button = ui.buttons[int(request)]
        except (IndexError, ValueError):
            raise ValueError("Type in the index of the correct option to choose from the buttons.")
        return CallbackRequest(payload=chosen_button.payload)
    return request


def turn_handler(
    in_request: str,
    ctx: Union[Context, str, dict],
    actor: Actor,
    true_out_response: Optional[str] = None,
):
    # Context.cast - gets an object type of [Context, str, dict] returns an object type of Context
    ctx = Context.cast(ctx)
    # Add in current context a next request of user
    in_request = process_request(ctx, in_request)
    ctx.add_request(in_request)
    # pass the context into actor and it returns updated context with actor response
    ctx = actor(ctx)
    # get last actor response from the context
    raw_response = ctx.last_response
    out_response = process_response(raw_response)
    # the next condition branching needs for testing
    if true_out_response is not None and true_out_response != out_response:
        msg = f"in_request={in_request} -> true_out_response != out_response: {true_out_response} != {out_response}"
        raise Exception(msg)
    else:
        logging.info(f"in_request={in_request} -> {out_response}")
    return out_response, ctx


def run_test(testing_dialog: list, actor: Actor):
    ctx = {}
    for in_request, true_out_response in testing_dialog:
        _, ctx = turn_handler(in_request, ctx, actor, true_out_response=true_out_response)


# interactive mode
def run_interactive_mode(actor: Actor):
    ctx = {}
    while True:
        in_request = input("type your answer: ")
        _, ctx = turn_handler(in_request, ctx, actor)
