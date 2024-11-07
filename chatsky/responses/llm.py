from typing import Union, Callable, Type
from chatsky.core.message import Message
from chatsky.core.context import Context
from chatsky.core.pipeline import Pipeline
from langchain_core.messages import SystemMessage
from chatsky.llm.utils import message_to_langchain
from pydantic import BaseModel
from chatsky.core.script_function import BaseResponse


class LLMResponse(BaseResponse):
    def __call__(
        self,
        model_name: str,
        prompt: str = "",
        history: int = 5,
        filter_func: Callable = lambda *args: True,
        message_schema: Union[None, Type[Message], Type[BaseModel]] = None,
        max_size: int = 1000,
    ):
        """
        Basic function for receiving LLM responses.
        :param ctx: Context object. (Assigned automatically)
        :param pipeline: Pipeline object. (Assigned automatically)
        :param model_name: Name of the model from the `Pipeline.models` dictionary.
        :param prompt: Prompt for the model.
        :param history: Number of messages to keep in history. `-1` for full history.
        :param filter_func: filter function to filter messages that will go the models context.
        :param max_size: Maximum size of any message in chat in symbols. If exceed the limit will raise ValueError.

        :raise ValueError: If any message longer than `max_size`.
        """

        async def wrapped(ctx: Context, pipeline: Pipeline) -> Message:
            model = pipeline.models[model_name]
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
                        await message_to_langchain(Message(global_prompt), pipeline=pipeline, source="system")
                    )
                if "local_prompt" in current_misc:
                    local_prompt = current_misc["local_prompt"]
                    history_messages.append(
                        await message_to_langchain(Message(local_prompt), pipeline=pipeline, source="system")
                    )
                if "prompt" in current_misc:
                    node_prompt = current_misc["prompt"]
                    history_messages.append(
                        await message_to_langchain(Message(node_prompt), pipeline=pipeline, source="system")
                    )

            # iterate over context to retrieve history messages
            if not (history == 0 or len(ctx.responses) == 0 or len(ctx.requests) == 0):
                pairs = zip(
                    [ctx.requests[x] for x in range(1, len(ctx.requests) + 1)],
                    [ctx.responses[x] for x in range(1, len(ctx.responses) + 1)],
                )
                if history != -1:
                    for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)[-history:]):
                        history_messages.append(await message_to_langchain(req, pipeline=pipeline, max_size=max_size))
                        history_messages.append(
                            await message_to_langchain(resp, pipeline=pipeline, source="ai", max_size=max_size)
                        )
                else:
                    # TODO: Fix redundant code
                    for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)):
                        history_messages.append(await message_to_langchain(req, pipeline=pipeline, max_size=max_size))
                        history_messages.append(
                            await message_to_langchain(resp, pipeline=pipeline, source="ai", max_size=max_size)
                        )

            if prompt:
                msg = await __prompt_to_message(prompt, ctx)
                history_messages.append(await message_to_langchain(msg, pipeline=pipeline, source="system"))
            history_messages.append(
                await message_to_langchain(ctx.last_request, pipeline=pipeline, source="human", max_size=max_size)
            )
            return await model.respond(history_messages, message_schema=message_schema)

        return wrapped


async def __prompt_to_message(prompt, ctx):
    if isinstance(prompt, str):
        return Message(prompt)
    elif isinstance(prompt, BaseResponse):
        return await prompt(ctx)
