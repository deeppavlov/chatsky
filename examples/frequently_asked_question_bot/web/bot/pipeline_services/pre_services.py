"""
Pre Services
---
This module defines services that process user requests before script transition.
"""
from dff.script import Context
from langdetect import detect_langs

from ..faq_model.model import find_similar_question

PROCESSED_LANGUAGES = ["en", "de", "fr", "es", "ru", "zh-cn"]


def language_processor(ctx: Context):
    """Store the user language; the language is detected from the last user utterance.
    The value can be one of: English, German, Spanish, French, Mandarin Chinese or Russian.
    """
    last_request = ctx.last_request
    if last_request is None or last_request.text is None:
        return
    if last_request.annotations is None:
        last_request.annotations = {}
    else:
        if last_request.annotations.get("user_language") is not None:
            return

    candidate_languages = detect_langs(last_request.text)
    if len(candidate_languages) == 0:
        last_request.annotations["user_language"] = "en"
    else:
        most_probable_language = candidate_languages[0]
        if most_probable_language.prob < 0.3:
            last_request.annotations["user_language"] = "en"
        elif most_probable_language.lang not in PROCESSED_LANGUAGES:
            last_request.annotations["user_language"] = "en"
        else:
            last_request.annotations["user_language"] = most_probable_language.lang

    ctx.last_request = last_request


def question_processor(ctx: Context):
    """Store the most similar question to user's query in the `annotations` field of a message."""
    last_request = ctx.last_request
    if last_request is None or last_request.text is None:
        return
    if last_request.annotations is None:
        last_request.annotations = {}
    else:
        if last_request.annotations.get("similar_question") is not None:
            return

    language = last_request.annotations["user_language"]
    last_request.annotations["similar_question"] = find_similar_question(last_request.text, language)

    ctx.last_request = last_request


services = [language_processor, question_processor]  # pre-services run before bot sends a response
