"""
Filters.
---------
This module contains a collection of basic functions for history filtering to avoid cluttering LLMs context window.
"""

from chatsky.script.core.message import Message

def is_important(msg: Message) -> bool:
    if msg.misc["important"]:
        return True
    return False

def from_the_model(msg: Message, model_name: str) -> bool:
    return msg.annotation.__generated_by_model__ == model_name
