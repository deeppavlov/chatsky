"""
LLM methods.
---------
In this file stored unified functions for some basic condition cases
including regex search, semantic distance (cosine) etc.
"""

from chatsky.script.core.message import Message
from chatsky.script import Context
from chatsky.pipeline import Pipeline
import re
from pydantic import BaseModel
import abc


class BaseMethod(BaseModel, abc.ABC):
    @abc.abstractmethod
    async def __call__(self, ctx: Context, model_result: str) -> bool:
        raise NotImplementedError


class Contains(BaseMethod):
    pattern: str

    async def __call__(self, ctx: Context, model_result: str, pattern: str = "") -> bool:
        print("Model result:", model_result)
        return await bool(self.pattern.lower() in model_result.lower())
