"""
LLM Conditions
--------------
This module provides LLM-based conditions.
"""

from chatsky.core import BaseCondition, Context
from chatsky.llm.methods import BaseMethod
from chatsky.llm.llm_api import BaseLLMScriptFunction


class LLMCondition(BaseCondition, BaseLLMScriptFunction):
    """
    LLM-based condition.
    Uses prompt to produce result from model and evaluates the result using given method.
    """

    method: BaseMethod
    """
    Method that takes model's output and returns boolean.
    """

    async def call(self, ctx: Context) -> bool:
        model = ctx.pipeline.models[self.llm_model_name]

        history_messages = []
        history_messages.extend(
            await self._get_langchain_context(
                ctx=ctx,
            )
        )

        return await model.condition(history_messages, self.method)
