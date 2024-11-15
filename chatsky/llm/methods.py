"""
LLM methods
-----------
In this file stored unified functions for some basic condition cases
including regex search, semantic distance (cosine) etc.
"""

from chatsky.core.context import Context
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

    async def model_result_to_text(self, model_result: LLMResult) -> str:
        """
        Converts raw model generation to a string.
        """
        return model_result.generations[0][0].text


class Contains(BaseMethod):
    """
    Simple method to check if a string contains a pattern.

    :param str pattern: pattern to check

    :return: True if pattern is contained in model result
    :rtype: bool
    """

    pattern: str

    async def __call__(self, ctx: Context, model_result: LLMResult) -> bool:
        text = await self.model_result_to_text(model_result)
        return bool(self.pattern.lower() in text.lower())


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
        try:
            result = model_result.generations[0][0].generation_info["logprobs"]["content"][0]["top_logprobs"]
        except ValueError:
            raise ValueError("LogProb method can only be applied to OpenAI models.")
        for tok in result:
            if tok["token"] == self.target_token and tok["logprob"] > self.threshold:
                return True

        return False
