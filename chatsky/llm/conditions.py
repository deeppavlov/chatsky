"""
LLM conditions.
---------
In this file stored unified functions for some basic condition cases
including regex search, semantic distance (cosine) etc.
"""

from chatsky.script.core.message import Message

def regex_search(pattern: str) -> bool:
    pass

def semantic_distance(target: str | Message, threshold: float) -> bool:
    pass