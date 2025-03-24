"""
LLM methods
-----------
This module provides basic methods to support LLM conditions.
These methods return bool values based on LLM result.
"""

import abc

from pydantic import BaseModel

from chatsky.core.context import Context
from chatsky.llm._langchain_imports import LLMResult


class BaseMethod(BaseModel, abc.ABC):
    """
    Base class to evaluate models response as condition.
    """

    @abc.abstractmethod
    async def __call__(self, ctx: Context, model_result: LLMResult) -> bool:
        """
        Determine if result of an LLM invocation satisfies the condition of this method.

        :param ctx: Current dialog context.
        :param model_result: Result of langchain model's invoke.

        """
        raise NotImplementedError

    def model_result_to_text(self, model_result: LLMResult) -> str:
        """
        Extract text from raw model result.
        """
        return model_result.generations[0][0].text


class Contains(BaseMethod):
    """
    Simple method to check if a string contains a pattern.
    """

    pattern: str
    """
    Pattern that will be searched in model_result.
    """

    async def __call__(self, ctx: Context, model_result: LLMResult) -> bool:
        """
        :return: True if pattern is contained in model_result.
        """
        text = self.model_result_to_text(model_result)
        return self.pattern.lower() in text.lower()


class LogProb(BaseMethod):
    """
    Method to check whether a target token's log probability is higher than a threshold.
    """

    target_token: str
    """
    Token to check (e.g. `"TRUE"`)
    """
    threshold: float = -0.5
    """
    Threshold to bypass. by default `-0.5`
    """

    async def __call__(self, ctx: Context, model_result: LLMResult) -> bool:
        """
        :return: True if logprob of the token is higher than threshold.
        """
        try:
            result = model_result.generations[0][0].generation_info["logprobs"]["content"][0]["top_logprobs"]
        except ValueError:
            raise ValueError("LogProb method can only be applied to OpenAI models.")
        for tok in result:
            if tok["token"] == self.target_token and tok["logprob"] > self.threshold:
                return True

        return False
