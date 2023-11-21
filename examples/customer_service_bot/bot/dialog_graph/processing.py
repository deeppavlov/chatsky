"""
Processing
----------
This module contains processing routines for the customer service
chat bot.
"""
import re
from string import punctuation
from dff.script import Context
from dff.pipeline import Pipeline
from api import chatgpt, intent_catcher
from . import consts


def extract_intents():
    """
    Extract intents from intent catcher response.
    """

    def extract_intents_inner(ctx: Context, _: Pipeline) -> Context:
        ctx.misc[consts.INTENTS] = intent_catcher.get_intents(ctx.last_request)
        return ctx

    return extract_intents_inner


def clear_intents():
    """
    Clear intents container.
    """

    def clear_intents_inner(ctx: Context, _: Pipeline) -> Context:
        ctx.misc[consts.INTENTS] = []
        return ctx

    return clear_intents_inner


def clear_slots():
    """
    Clear slots container.
    """

    def clear_slots_inner(ctx: Context, _: Pipeline) -> Context:
        ctx.misc[consts.SLOTS] = {}
        return ctx

    return clear_slots_inner


def generate_response():
    """
    Store ChatGPT output and ChatGPT coherence measure in the context.
    """
    expression = re.compile(r"true", re.IGNORECASE)

    def generate_response_inner(ctx: Context, _: Pipeline) -> Context:
        if ctx.validation:
            return ctx

        chatgpt_output = chatgpt.get_output(ctx.last_request.text)
        ctx.misc[consts.CHATGPT_OUTPUT] = chatgpt_output
        coherence_output = chatgpt.get_coherence(ctx.last_request.text, chatgpt_output)
        ctx.misc[consts.CHATGPT_COHERENCE] = True if re.search(expression, coherence_output) else False
        return ctx

    return generate_response_inner


def extract_item():
    """
    Extract item slot.
    """
    expression = re.compile(r".+")

    def extract_item_inner(ctx: Context, _: Pipeline) -> Context:
        if ctx.validation:
            return ctx

        text: str = ctx.last_request.text
        search = re.search(expression, text)
        if search is not None:
            group = search.group()
            ctx.misc[consts.SLOTS]["items"] = [item.strip(punctuation) for item in group.split(", ")]
        return ctx

    return extract_item_inner


def extract_payment_method():
    """Extract payment method slot."""
    expression = re.compile(r"(card|cash)", re.IGNORECASE)

    def extract_payment_method_inner(ctx: Context, _: Pipeline) -> Context:
        if ctx.validation:
            return ctx

        text: str = ctx.last_request.text
        search = re.search(expression, text)
        if search is not None:
            ctx.misc[consts.SLOTS]["payment_method"] = search.group()
        return ctx

    return extract_payment_method_inner


def extract_delivery():
    """
    Extract delivery slot.
    """
    expression = re.compile(r"(pickup|deliver)", re.IGNORECASE)

    def extract_delivery_inner(ctx: Context, _: Pipeline) -> Context:
        if ctx.validation:
            return ctx

        text: str = ctx.last_request.text
        search = re.search(expression, text)
        if search is not None:
            ctx.misc[consts.SLOTS]["delivery"] = search.group()
        return ctx

    return extract_delivery_inner
