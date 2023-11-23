"""
Pre Services
---
This module defines services that process user requests before script transition.
"""
from dff.script import Context

from ..faq_model.model import find_similar_question


def question_processor(ctx: Context):
    """Store the most similar question to user's query in the `annotations` field of a message."""
    last_request = ctx.last_request
    if last_request is None or last_request.text is None:
        return
    else:
        if last_request.annotations is None:
            last_request.annotations = {}
        else:
            if last_request.annotations.get("similar_question") is not None:
                return
        if last_request.text is None:
            last_request.annotations["similar_question"] = None
        else:
            last_request.annotations["similar_question"] = find_similar_question(last_request.text)

    ctx.last_request = last_request


services = [question_processor]  # pre-services run before bot sends a response
