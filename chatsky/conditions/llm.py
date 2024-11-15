"""
LLM Conditions
--------------
This module provides LLM-based conditions.
"""
from chatsky.llm.methods import BaseMethod
from chatsky.core import BaseCondition, Context


class LLMCondition(BaseCondition):
    """
    LLM-based condition.
    Uses prompt to produce result from model and evaluates the result using given method.
    """

    model_name: str
    """
    Key of the model in the :py:attr:`~chatsky.core.pipeline.Pipeline.models` dictionary.
    """
    prompt: str
    """
    Condition prompt.
    """
    method: BaseMethod
    """
    Method that takes model's output and returns boolean.
    """

    async def call(self, ctx: Context) -> bool:
        model = ctx.pipeline.models[self.model_name]
        return await model.condition(ctx, self.prompt, self.method)
