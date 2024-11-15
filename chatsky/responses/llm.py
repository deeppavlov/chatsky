from typing import Union, Type
from chatsky.core.message import Message
from chatsky.core.context import Context
from langchain_core.messages import SystemMessage
from chatsky.llm.utils import message_to_langchain, context_to_history
from chatsky.llm.filters import BaseFilter
from pydantic import BaseModel, Field
from chatsky.core.script_function import BaseResponse, AnyResponse


class LLMResponse(BaseResponse):
    """
    Basic function for receiving LLM responses.
    :param model_name: Name of the model from the `Pipeline.models` dictionary.
    :param prompt: Prompt for the model.
    :param history: Number of messages to keep in history. `-1` for full history.
    :param filter_func: filter function to filter messages that will go the models context.
    :param max_size: Maximum size of any message in chat in symbols. If exceed the limit will raise ValueError.

    :raise ValueError: If any message longer than `max_size`.
    """

    model_name: str
    prompt: AnyResponse = Field(default="", validate_default=True)
    history: int = 5
    filter_func: BaseFilter = lambda *args: True
    message_schema: Union[None, Type[Message], Type[BaseModel]] = None
    max_size: int = 1000

    async def call(self, ctx: Context) -> Message:

        model = ctx.pipeline.models[self.model_name]
        if model.system_prompt == "":
            history_messages = []
        else:
            history_messages = [SystemMessage(model.system_prompt)]
        current_node = ctx.current_node
        current_misc = current_node.misc if current_node is not None else None
        if current_misc is not None:
            # populate history with global and local prompts
            if "global_prompt" in current_misc:
                global_prompt = current_misc["global_prompt"]
                history_messages.append(
                    await message_to_langchain(Message(global_prompt), ctx=ctx, source="system")
                )
            if "local_prompt" in current_misc:
                local_prompt = current_misc["local_prompt"]
                history_messages.append(
                    await message_to_langchain(Message(local_prompt), ctx=ctx, source="system")
                )
            if "prompt" in current_misc:
                node_prompt = current_misc["prompt"]
                history_messages.append(
                    await message_to_langchain(Message(node_prompt), ctx=ctx, source="system")
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

        if self.prompt:
            msg = await self.prompt(ctx)
            history_messages.append(await message_to_langchain(msg, ctx=ctx, source="system"))
        history_messages.append(
            await message_to_langchain(ctx.last_request, ctx=ctx, source="human", max_size=self.max_size)
        )
        result = await model.respond(history_messages, message_schema=self.message_schema)

        if result.annotations:
            result.annotations["__generated_by_model__"] = self.model_name
        else:
            result.annotations = {"__generated_by_model__": self.model_name}

        return result
