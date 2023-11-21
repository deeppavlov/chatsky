"""
Pre Services
---
This module defines services that process user requests before script transition.
"""
from dff.script import Context

from faq_model.model import find_similar_questions


def question_processor(ctx: Context):
    """Store questions similar to user's query in the `annotations` field of a message."""
    last_request = ctx.last_request
    if last_request is None:
        return
    else:
        if last_request.annotations is None:
            last_request.annotations = {}
        else:
            if last_request.annotations.get("similar_questions") is not None:
                return
        if last_request.text is None:
            last_request.annotations["similar_questions"] = None
        else:
            last_request.annotations["similar_questions"] = find_similar_questions(last_request.text)

    ctx.set_last_request(last_request)


services = [question_processor]  # pre-services run before bot sends a response
