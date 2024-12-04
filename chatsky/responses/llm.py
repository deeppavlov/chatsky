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
from chatsky.llm.utils import message_to_langchain, context_to_history
from chatsky.llm._langchain_imports import SystemMessage, check_langchain_available
from chatsky.llm.filters import BaseHistoryFilter
from chatsky.core.script_function import BaseResponse, AnyResponse


class LLMResponse(BaseResponse):
    """
    Basic function for receiving LLM responses.
    :param model_name: Name of the model from the `Pipeline.models` dictionary.
    :param prompt: Prompt for the model.
    :param history: Number of messages to keep in history. `-1` for full history.
    :param filter_func: Filter function to filter messages that will go the models context.
    :param max_size: Maximum size of any message in chat in symbols. If exceed the limit will raise ValueError.

    :raise ValueError: If any message longer than `max_size`.
    """

    model_name: str
    prompt: AnyResponse = Field(default="", validate_default=True)
    history: int = 5
    filter_func: BaseHistoryFilter = BaseHistoryFilter()
    message_schema: Union[None, Type[Message], Type[BaseModel]] = None
    max_size: int = 1000

    async def call(self, ctx: Context) -> Message:
        check_langchain_available()
        model = ctx.pipeline.models[self.model_name]
        if model.system_prompt == "":
            history_messages = []
        else:
            history_messages = [SystemMessage(model.system_prompt)]
        current_node = ctx.current_node
        current_misc = current_node.misc
        if current_misc is not None:
            # populate history with global and local prompts
            for prompt in ("global_prompt", "local_prompt", "prompt"):
                if prompt in current_misc:
                    current_prompt = current_misc[prompt]
                    if isinstance(current_prompt, BaseResponse):
                        current_prompt = await current_prompt(ctx=ctx)
                        history_messages.append(await message_to_langchain(current_prompt, ctx=ctx, source="system"))
                    elif isinstance(current_prompt, str):
                        history_messages.append(
                            await message_to_langchain(Message(current_prompt), ctx=ctx, source="system")
                        )

        # iterate over context to retrieve history messages
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

        msg = await self.prompt(ctx)
        if msg.text:
            history_messages.append(await message_to_langchain(msg, ctx=ctx, source="system"))

        history_messages.append(
            await message_to_langchain(ctx.last_request, ctx=ctx, source="human", max_size=self.max_size)
        )
        logging.debug(f"History: {history_messages}")
        result = await model.respond(history_messages, message_schema=self.message_schema)

        if result.annotations:
            result.annotations["__generated_by_model__"] = self.model_name
        else:
            result.annotations = {"__generated_by_model__": self.model_name}

        return result
