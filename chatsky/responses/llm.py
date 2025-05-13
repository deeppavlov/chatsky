"""
LLM responses
--------------
Responses based on LLM_API calling.
"""

from typing import Union, Type, Optional

from pydantic import BaseModel, Field

from chatsky.core.message import Message
from chatsky.core.context import Context
from chatsky.llm.langchain_context import get_langchain_context
from chatsky.llm.filters import BaseHistoryFilter, DefaultFilter
from chatsky.llm.prompt import Prompt, PositionConfig
from chatsky.core.script_function import BaseResponse


class LLMResponse(BaseResponse):
    """
    Basic function for receiving LLM responses.
    Uses prompt to produce result from model.
    """

    llm_model_name: str
    """
    Key of the model in the :py:attr:`~chatsky.core.pipeline.Pipeline.models` dictionary.
    """
    prompt: Prompt = Field(default="", validate_default=True)
    """
    Response prompt.
    """
    history: int = 5
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
    message_schema: Union[None, Type[Message], Type[BaseModel]] = None
    """
    Schema for model output validation.
    """
    max_size: int = 5000
    """
    Maximum size of any message in chat in symbols.
    If a message exceeds the limit it will not be sent to the LLM and a warning
    will be produced.
    """

    async def call(self, ctx: Context) -> Message:
        model = ctx.pipeline.models[self.llm_model_name]
        history_messages = []

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

        result = await model.respond(history_messages, message_schema=self.message_schema)

        if result.annotations:
            result.annotations["__generated_by_model__"] = self.llm_model_name
        else:
            result.annotations = {"__generated_by_model__": self.llm_model_name}

        return result
