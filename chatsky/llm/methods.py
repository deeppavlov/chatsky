"""
LLM methods.
---------
In this file stored unified functions for some basic condition cases
including regex search, semantic distance (cosine) etc.
"""

from chatsky.script import Context
from pydantic import BaseModel
import abc


class BaseMethod(BaseModel, abc.ABC):
    """
    Base class to evaluate models response as condition.
    """
    @abc.abstractmethod
    async def __call__(self, ctx: Context, model_result: str) -> bool:
        raise NotImplementedError


class Contains(BaseMethod):
    """
    Simple method to check if a string contains a pattern.

    :param str pattern: pattern to check

    :return: True if pattern is contained in model result
    :rtype: bool
    """
    pattern: str

    async def __call__(self, ctx: Context, model_result: str) -> bool:
        print("Model result:", model_result)
        return await bool(self.pattern.lower() in model_result.lower())


class LogProb(BaseMethod):
    treshold: float = 0.7
    async def __call__(self, ctx: Context, model_result: dict) -> bool:
        raise NotImplementedError