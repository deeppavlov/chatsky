"""
Script
--------
This module defines a script that the bot follows during conversation.
"""
from dff.script import RESPONSE, TRANSITIONS, LOCAL
import dff.script.conditions as cnd
from dff.messengers.telegram import TelegramMessage

from .responses import answer_question, suggest_similar_questions
from .conditions import received_button_click, received_text

script = {
    "service_flow": {
        "start_node": {
            TRANSITIONS: {("qa_flow", "welcome_node"): cnd.exact_match(TelegramMessage(text="/start"))},
        },
        "fallback_node": {
            RESPONSE: TelegramMessage(text="Something went wrong. Use `/restart` to start over."),
            TRANSITIONS: {("qa_flow", "welcome_node"): cnd.exact_match(TelegramMessage(text="/restart"))},
        },
    },
    "qa_flow": {
        LOCAL: {
            TRANSITIONS: {
                ("qa_flow", "suggest_questions"): received_text,
                ("qa_flow", "answer_question"): received_button_click,
            },
        },
        "welcome_node": {
            RESPONSE: TelegramMessage(text="Welcome! Ask me questions about Arch Linux."),
        },
        "suggest_questions": {
            RESPONSE: suggest_similar_questions,
        },
        "answer_question": {
            RESPONSE: answer_question,
        },
    },
}
