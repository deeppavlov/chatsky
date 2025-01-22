"""
LLM responses.
--------------
Responses based on LLM_API calling.
"""

from typing import Union, Type
import logging

from pydantic import BaseModel, Field

from chatsky.core.message import Message
from chatsky.core.context import Context
from chatsky.llm.langchain_context import message_to_langchain, context_to_history, get_langchain_context
from chatsky.llm._langchain_imports import check_langchain_available
from chatsky.llm.filters import BaseHistoryFilter, DefaultFilter
from chatsky.core.script_function import BaseResponse, AnyResponse


class LLMResponse(BaseResponse):
    """
    Basic function for receiving LLM responses.
    Uses prompt to produce result from model.
    """

    llm_model_name: str
    """
    Key of the model in the :py:attr:`~chatsky.core.pipeline.Pipeline.models` dictionary.
    """
    prompt: AnyResponse = Field(default="", validate_default=True)
    """
    Response prompt.
    """
    history: int = 5
    """
    Number of dialogue turns to keep in history. `-1` for full history.
    """
    filter_func: BaseHistoryFilter = Field(default_factory=DefaultFilter)
    """
    Filter function to filter messages that will go the models context.
    """
    message_schema: Union[None, Type[Message], Type[BaseModel]] = None
    """
    Schema for model output validation.
    """
    max_size: int = 1000
    """
    Maximum size of any message in chat in symbols. If exceed the limit will raise ValueError.
    """

    async def call(self, ctx: Context) -> Message:
        check_langchain_available()
        model = ctx.pipeline.models[self.llm_model_name]
        history_messages = []

        # iterate over context to retrieve history messages
        if not (self.history == 0 or len(ctx.responses) == 0 or len(ctx.requests) == 0):
            logging.debug("Retrieving context history.")
            history_messages.extend(
                await get_langchain_context(
                    system_prompt=await model.system_prompt(ctx),
                    ctx=ctx,
                    call_prompt="",
                    length=self.history,
                    filter_func=self.filter_func,
                    llm_model_name=self.llm_model_name,
                    max_size=self.max_size,
                )
            )
        else:
            logging.debug("No context history to retrieve.")

        msg = await self.prompt(ctx)
        if msg.text:
            history_messages.append(await message_to_langchain(msg, ctx=ctx, source="system"))

        history_messages.append(
            await message_to_langchain(ctx.last_request, ctx=ctx, source="human", max_size=self.max_size)
        )
        logging.debug(f"History: {history_messages}")
        result = await model.respond(history_messages, message_schema=self.message_schema)

        if result.annotations:
            result.annotations["__generated_by_model__"] = self.llm_model_name
        else:
            result.annotations = {"__generated_by_model__": self.llm_model_name}

        return result
