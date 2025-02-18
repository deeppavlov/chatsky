"""
LLM Conditions
--------------
This module provides LLM-based conditions.
"""

from pydantic import Field
from typing import Optional

from chatsky.core import BaseCondition, Context
from chatsky.core.script_function import AnyResponse
from chatsky.llm.methods import BaseMethod
from chatsky.llm.langchain_context import get_langchain_context
from chatsky.llm.filters import BaseHistoryFilter, DefaultFilter
from chatsky.llm.prompt import PositionConfig, Prompt


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
    Number of dialogue turns aside from the current one to keep in history. `-1` for full history.
    """
    filter_func: BaseHistoryFilter = Field(default_factory=DefaultFilter)
    """
    Filter function to filter messages in history.
    """
    prompt_misc_filter: str = Field(default=r"prompt")
    """
    Regular expression to find prompts by key names in MISC dictionary.
    """
    position_config: Optional[PositionConfig] = None
    """
    Config for positions of prompts and messages in history.
    """
    max_size: int = 5000
    """
    Maximum size of any message in chat in symbols.
    If a message exceeds the limit it will not be sent to the LLM and a warning
    will be produced.
    """
    method: BaseMethod
    """
    Method that takes model's output and returns boolean.
    """

    async def call(self, ctx: Context) -> bool:
        model = ctx.pipeline.models[self.llm_model_name]

        history_messages = []
        history_messages.extend(
            await get_langchain_context(
                system_prompt=await model.system_prompt(ctx),
                ctx=ctx,
                call_prompt=Prompt(message=self.prompt),
                prompt_misc_filter=self.prompt_misc_filter,
                position_config=self.position_config or model.position_config,
                length=self.history,
                filter_func=self.filter_func,
                llm_model_name=self.llm_model_name,
                max_size=self.max_size,
            )
        )

        return await model.condition(history_messages, self.method)
