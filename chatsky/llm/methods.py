"""
LLM methods.
---------
In this file stored unified functions for some basic condition cases
including regex search, semantic distance (cosine) etc.
"""

from chatsky.script import Context
from pydantic import BaseModel
from langchain_core.outputs.llm_result import LLMResult
import abc


class BaseMethod(BaseModel, abc.ABC):
    """
    Base class to evaluate models response as condition.
    """
    @abc.abstractmethod
    async def __call__(self, ctx: Context, model_result: LLMResult) -> bool:
        raise NotImplementedError


class Contains(BaseMethod):
    """
    Simple method to check if a string contains a pattern.

    :param str pattern: pattern to check

    :return: True if pattern is contained in model result
    :rtype: bool
    """
    pattern: str

    async def __call__(self, ctx: Context, model_result: LLMResult) -> bool:
        return bool(self.pattern.lower() in model_result.generations[0][0].text.lower())


class LogProb(BaseMethod):
    """
    Method to check whether a target token's log probability is higher then a threshold.

    :param str target_token: token to check (e.g. `"TRUE"`)
    :param float threshold: threshold to bypass. by default `-0.5`

    :return: True if logprob is higher then threshold
    :rtype: bool
    """
    target_token: str
    threshold: float = -0.5
    async def __call__(self, ctx: Context, model_result: LLMResult) -> bool:
        result = model_result.generations[0][0].generation_info['logprobs']['content'][0]['top_logprobs']
        for tok in result:
            if tok["token"] == self.target_token and tok["logprob"] > self.threshold:
                return True

        return False
