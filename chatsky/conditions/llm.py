"""
LLM Conditions
--------------
This module provides LLM-based conditions.
"""

from pydantic import Field

from chatsky.core import BaseCondition, Context
from chatsky.core.script_function import AnyResponse
from chatsky.llm.methods import BaseMethod
from chatsky.llm.utils import context_to_history, message_to_langchain
from chatsky.llm.filters import BaseHistoryFilter, DefaultFilter


class LLMCondition(BaseCondition):
    """
    LLM-based condition.
    Uses prompt to produce result from model and evaluates the result using given method.
    """

    model_name: str
    """
    Key of the model in the :py:attr:`~chatsky.core.pipeline.Pipeline.models` dictionary.
    """
    prompt: AnyResponse = Field(default="", validate_default=True)
    """
    Condition prompt.
    """
    history: int = 1
    """
    Number of dialogue turns to keep in history. `-1` for full history.
    """
    filter_func: BaseHistoryFilter = Field(default_factory=DefaultFilter)
    """
    Filter function to filter messages that will go the models context.
    """
    max_size: int = 1000
    """
    Maximum size of any message in chat in symbols. If exceed the limit will raise ValueError.
    """
    method: BaseMethod
    """
    Method that takes model's output and returns boolean.
    """

    async def call(self, ctx: Context) -> bool:
        model = ctx.pipeline.models[self.model_name]

        if model.system_prompt == "":
            history_messages = []
        else:
            history_messages = [message_to_langchain(model.system_prompt, ctx=ctx, source="system")]

        if not (self.history == 0 or len(ctx.responses) == 0 or len(ctx.requests) == 0):
            history_messages.extend(
                await context_to_history(
                    ctx=ctx,
                    length=self.history,
                    filter_func=self.filter_func,
                    model_name=self.model_name,
                    max_size=self.max_size,
                )
            )

        history_messages.append(
            await message_to_langchain(self.prompt, ctx=ctx, source="system", max_size=self.max_size)
        )
        history_messages.append(
            await message_to_langchain(ctx.last_request, ctx=ctx, source="human", max_size=self.max_size)
        )

        return await model.condition(history_messages, self.method)
