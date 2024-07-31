"""
LLM conditions.
---------
In this file stored unified functions for some basic condition cases
including regex search, semantic distance (cosine) etc.
"""

from chatsky.script.core.message import Message
from chatsky.script import Context
from chatsky.pipeline import Pipeline
import re


def regex_search(pattern: str):
    def _(ctx: Context, _: Pipeline) -> bool:
        return bool(re.search(pattern, ctx.last_request.text))

    return _


def semantic_distance(target: str | Message, threshold: float):
    def _(ctx: Context, _: Pipeline) -> bool:
        pass

    return _
