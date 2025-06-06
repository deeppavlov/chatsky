"""
LLM responses
--------------
Responses based on LLM_API calling.
"""

from typing import Union, Type

from pydantic import BaseModel

from chatsky.core.message import Message
from chatsky.core.context import Context
from chatsky.llm.llm_api import BaseLLMScriptFunction
from chatsky.core.script_function import BaseResponse


class LLMResponse(BaseResponse, BaseLLMScriptFunction):
    """
    Basic function for receiving LLM responses.
    Uses prompt to produce result from model.
    """

    message_schema: Union[None, Type[Message], Type[BaseModel]] = None
    """
    Schema for model output validation.
    """
    history: int = 5

    async def call(self, ctx: Context) -> Message:
        model = ctx.pipeline.models[self.llm_model_name]
        history_messages = []

        history_messages.extend(
            await self._get_langchain_context(
                ctx=ctx,
            )
        )

        result = await model.respond(history_messages, message_schema=self.message_schema)

        if result.annotations:
            result.annotations["__generated_by_model__"] = self.llm_model_name
        else:
            result.annotations = {"__generated_by_model__": self.llm_model_name}

        return result
