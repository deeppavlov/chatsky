"""
Response
--------
This module contains response customization functions.
"""
from dff.script import Context, Message
from dff.pipeline import Pipeline

from . import consts

FALLBACK_RESPONSE = (
    "I'm afraid I cannot elaborate on this subject. If you have any other questions, feel free to ask them."
)


def choose_response(ctx: Context, _: Pipeline) -> Message:
    """
    Return ChatGPT response if it is coherent, fall back to
    predetermined response otherwise.
    """
    if ctx.validation:
        return Message()
    coherence = ctx.misc[consts.CHATGPT_COHERENCE]
    response = ctx.misc[consts.CHATGPT_OUTPUT]
    return Message(text=(response if coherence else FALLBACK_RESPONSE))


def confirm(ctx: Context, _: Pipeline) -> Message:
    if ctx.validation:
        return Message()
    msg_text = (
        "We registered your transaction. "
        + f"Requested titles are: {', '.join(ctx.misc[consts.SLOTS]['items'])}. "
        + f"Delivery method: {ctx.misc[consts.SLOTS]['delivery']}. "
        + f"Payment method: {ctx.misc[consts.SLOTS]['payment_method']}. "
        + "Type `abort` to cancel, type `ok` to continue."
    )
    msg = Message(text=msg_text)
    return msg
