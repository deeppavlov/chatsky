"""
LLM methods.
---------
In this file stored unified functions for some basic condition cases
including regex search, semantic distance (cosine) etc.
"""

from chatsky.script import Context
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
import abc


class BaseMethod(BaseModel, abc.ABC):
    """
    Base class to evaluate models response as condition.
    """
    @abc.abstractmethod
    async def __call__(self, ctx: Context, model_result: BaseMessage) -> bool:
        raise NotImplementedError


class Contains(BaseMethod):
    """
    Simple method to check if a string contains a pattern.

    :param str pattern: pattern to check

    :return: True if pattern is contained in model result
    :rtype: bool
    """
    pattern: str

    async def __call__(self, ctx: Context, model_result: BaseMessage) -> bool:
        print("Model result:", model_result)
        return bool(self.pattern.lower() in model_result.content.lower())


class LogProb(BaseMethod):
    target_token: str
    treshold: float = 0.7
    async def __call__(self, ctx: Context, model_result: BaseMessage) -> bool:
        result = model_result.response_metadata["logprobs"]["content"]
        for tok in result:
            if tok["token"] == self.target_token and tok["logprob"] > self.treshold:
                return True

        return False
