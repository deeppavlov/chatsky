"""
Responses
---------
This module defines different responses the bot gives.
"""

from dff.script import Context
from dff.script import Message
from dff.pipeline import Pipeline
from ..faq_model.model import faq


def get_bot_answer(question: str) -> Message:
    """The Message the bot will return as an answer if the most similar question is `question`."""
    return Message(text=f"Q: {question} <br> A: {faq[question]}")


FALLBACK_ANSWER = Message(
    text='I don\'t have an answer to that question. '
         'You can find FAQ <a href="https://wiki.archlinux.org/title/Frequently_asked_questions">here</a>.',
)
"""Fallback answer that the bot returns if user's query is not similar to any of the questions."""


FIRST_MESSAGE = Message(
    text="Welcome! Ask me questions about Arch Linux."
)

FALLBACK_NODE_MESSAGE = Message(
    text="Something went wrong.\n"
         "You may continue asking me questions about Arch Linux."
)


def answer_similar_question(ctx: Context, _: Pipeline):
    """Answer with the most similar question to user's query."""
    if ctx.validation:  # this function requires non-empty fields and cannot be used during script validation
        return Message()
    last_request = ctx.last_request
    if last_request is None:
        raise RuntimeError("No last requests.")
    if last_request.annotations is None:
        raise RuntimeError("No annotations.")
    similar_question = last_request.annotations.get("similar_question")

    if similar_question is None:  # question is not similar to any of the questions
        return FALLBACK_ANSWER
    else:
        return get_bot_answer(similar_question)
