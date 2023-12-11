"""
Responses
---------
This module defines different responses the bot gives.
"""

from dff.script import Context
from dff.script import Message
from dff.pipeline import Pipeline
from ..faq_model.model import faq, response_translations


def get_bot_answer(question: str, language: str) -> Message:
    """The Message the bot will return as an answer if the most similar question is `question`."""
    index = list(faq.keys()).index(question)
    return Message(text=f"A: {response_translations[language][index]}")


def get_fallback_answer(language: str):
    """Fallback answer that the bot returns if user's query is not similar to any of the questions."""
    fallbacks = {
        "en": "I don't have an answer to that question. ",
        "es": "No tengo una respuesta a esa pregunta. ",
        "fr": "Je n'ai pas de réponse à cette question. ",
        "de": "Ich habe keine Antwort auf diese Frage. ",
        "zh-cn": "我对这个问题没有答案。",
        "ru": "У меня нет ответа на этот вопрос. ",
    }

    return Message(
        text=fallbacks[language],
    )


FIRST_MESSAGE = Message(
    text="Welcome! Ask me questions about Deeppavlov.\n"
    "¡Bienvenido! Hazme preguntas sobre Deeppavlov.\n"
    "Bienvenue ! Posez-moi des questions sur Deeppavlov.\n"
    "Willkommen! Stellen Sie mir Fragen zu Deeppavlov.\n"
    "欢迎！向我询问有关Deeppavlov的问题。\n"
    "Добро пожаловать! Задайте мне вопросы о Deeppavlov."
)

FALLBACK_NODE_MESSAGE = Message(text="Something went wrong.\n" "You may continue asking me questions about Deeppavlov.")


def answer_similar_question(ctx: Context, _: Pipeline):
    """Answer with the most similar question to user's query."""
    if ctx.validation:  # this function requires non-empty fields and cannot be used during script validation
        return Message()
    last_request = ctx.last_request
    language = last_request.annotations["user_language"]
    if last_request is None:
        raise RuntimeError("No last requests.")
    if last_request.annotations is None:
        raise RuntimeError("No annotations.")
    similar_question = last_request.annotations.get("similar_question")

    if similar_question is None:  # question is not similar to any of the questions
        return get_fallback_answer(language)
    else:
        return get_bot_answer(similar_question, language)
