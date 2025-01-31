"""
LLM Conditions
--------------
This module provides LLM-based conditions.
"""

import logging
from pydantic import Field
from typing import Optional

from chatsky.core import BaseCondition, Context
from chatsky.core.script_function import AnyResponse
from chatsky.llm.methods import BaseMethod
from chatsky.llm.langchain_context import get_langchain_context
from chatsky.llm.filters import BaseHistoryFilter, DefaultFilter
from chatsky.llm.prompt import PositionConfig


class LLMCondition(BaseCondition):
    """
    LLM-based condition.
    Uses prompt to produce result from model and evaluates the result using given method.
    """

    llm_model_name: str
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
    prompt_misc_filter: str = Field(default=r"prompt")
    """
    idk
    """
    position_config: Optional[PositionConfig] = None
    """
    Defines prompts and messages positions in history sent to a LLM.
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
        model = ctx.pipeline.models[self.llm_model_name]

        history_messages = []
        # iterate over context to retrieve history messages
        logging.debug("Retrieving context history.")
        history_messages.extend(
            await get_langchain_context(
                system_prompt=await model.system_prompt(ctx),
                ctx=ctx,
                call_prompt=self.prompt,
                prompt_misc_filter=self.prompt_misc_filter,
                position_config=self.position_config or model.position_config,
                length=self.history,
                filter_func=self.filter_func,
                llm_model_name=self.llm_model_name,
                max_size=self.max_size,
            )
        )

        return await model.condition(history_messages, self.method)
