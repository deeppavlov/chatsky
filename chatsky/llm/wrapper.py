"""
LLM responses.
---------
Wrapper around langchain.
"""

try:
    from langchain_openai import ChatOpenAI
    from langchain_anthropic import ChatAnthropic
    from langchain_google_vertexai import ChatVertexAI
    from langchain_cohere import ChatCohere
    from langchain_mistralai import ChatMistralAI
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.language_models.chat_models import BaseChatModel
    langchain_available = True
except ImportError:
    langchain_available = False

import base64

from chatsky.script.core.message import Image, Message
from chatsky.script import Context
from chatsky.pipeline import Pipeline
from chatsky.llm.methods import BaseMethod

from typing import Union, Callable, Type
from pydantic import BaseModel


class LLM_API:
    """
    This class acts as a wrapper for all LLMs from langchain
    and handles message exchange between remote model and chatsky classes.
    """

    def __init__(
        self,
        model: BaseChatModel,
        system_prompt: str = "",
    ) -> None:
        """
        :param model: Model object.
        :param system_prompt: System prompt for the model.
        """
        self.__check_imports()
        self.model: BaseChatModel = model
        self.name = ""
        self.parser = StrOutputParser()
        self.system_prompt = system_prompt

    def __check_imports(self):
        if not langchain_available:
            raise ImportError("Langchain is not available. Please install it with `pip install chatsky[llm]`.")

    async def respond(
        self, history: list = [""], message_schema: Union[None, Type[Message], Type[BaseModel]] = None
    ) -> Message:
        if message_schema is None:
            result = await self.parser.ainvoke(await self.model.ainvoke(history))
            result = Message(text=result)

        elif issubclass(message_schema, Message):
            # Case if the message_schema desribes Message structure
            structured_model = await self.model.with_structured_output(message_schema)
            result = Message.model_validate(await structured_model.invoke(history))
        elif issubclass(message_schema, BaseModel):
            # Case if the message_schema desribes Message.text structure
            structured_model = await self.model.with_structured_output(message_schema)
            result = await structured_model.invoke(history)
            result = Message(text=str(result.json()))

        if result.annotations:
            result.annotations["__generated_by_model__"] = self.name
        else:
            result.annotations = {"__generated_by_model__": self.name}
        return result

    async def condition(self, prompt: str, method: BaseMethod):
        async def process_input(ctx: Context, _: Pipeline) -> bool:
            condition_history = [await message_to_langchain(Message(prompt), pipeline=_, source="system"),
                await message_to_langchain(ctx.last_request, pipeline=_, source="human")]
            result = method(ctx, await self.model.ainvoke(condition_history))
            return result

        return process_input


def llm_response(model_name: str, prompt: str = "", history: int = 5, filter_func: Callable = lambda *args: True, message_schema: Union[None, Type[Message], Type[BaseModel]] = None):
    """
    Basic function for receiving LLM responses.
    :param ctx: Context object. (Assigned automatically)
    :param pipeline: Pipeline object. (Assigned automatically)
    :param model_name: Name of the model from the `Pipeline.models` dictionary.
    :param prompt: Prompt for the model.
    :param history: Number of messages to keep in history. `-1` for full history.
    :param filter_func: filter function to filter messages that will go the models context.
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
            if "prompt" in current_misc:
                node_prompt = current_misc["prompt"]
                history_messages.append(await message_to_langchain(Message(node_prompt), pipeline=pipeline, source="system"))
            if "global_prompt" in current_misc:
                global_prompt = current_misc["global_prompt"]
                history_messages.append(await message_to_langchain(Message(global_prompt), pipeline=pipeline, source="system"))
            if "local_prompt" in current_misc:
                local_prompt = current_misc["local_prompt"]
                history_messages.append(await message_to_langchain(Message(local_prompt), pipeline=pipeline, source="system"))

        # iterate over context to retrieve history messages
        if not (history == 0 or len(ctx.responses) == 0 or len(ctx.requests) == 0):
            pairs = zip(
                [ctx.requests[x] for x in range(len(ctx.requests))],
                [ctx.responses[x] for x in range(len(ctx.responses))],
            )
            if history != -1:
                for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)[-history:]):
                    history_messages.append(await message_to_langchain(req, pipeline=pipeline))
                    history_messages.append(await message_to_langchain(resp, pipeline=pipeline, source="ai"))
            else:
                # TODO: Fix redundant code
                for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)):
                    history_messages.append(await message_to_langchain(req, pipeline=pipeline))
                    history_messages.append(await message_to_langchain(resp, pipeline=pipeline, source="ai"))

        if prompt:
            history_messages.append(await message_to_langchain(Message(prompt), pipeline=pipeline, source="system"))
        history_messages.append(await message_to_langchain(ctx.last_request, pipeline=pipeline, source="human"))
        return await model.respond(history_messages, message_schema=message_schema)

    return wrapped


def llm_condition(model_name: str, prompt: str, method: BaseMethod):
    """
    Basic function for using LLM in condition cases.

    :param model_name: Key of the model from the `Pipeline.models` dictionary.
    :param prompt: Prompt for the model to use on users input.
    :param method: Method that takes models output and returns boolean.
    """

    async def wrapped(ctx, pipeline):
        model = pipeline.models[model_name]
        return await model.condition(prompt, method)

    return wrapped


async def __attachment_to_content(attachment: Image, iface) -> str:
    """
    Helper function to convert image to base64 string.
    """
    image_bytes = await attachment.get_bytes(iface)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    extension = str(attachment.source).split(".")[-1]
    if image_b64 == "" or extension is None:
        raise ValueError("Data image is not accessible.")
    image_b64 = f"data:image/{extension};base64,{image_b64}"
    return image_b64


async def message_to_langchain(message: Message, pipeline: Pipeline, source: str = "human", max_size: int=1000):
    """
    Creates a langchain message from a ~chatsky.script.core.message.Message object.

    :param Message message: ~chatsky.script.core.message.Message object.
    :param Pipeline pipeline: ~chatsky.pipeline.Pipeline object.
    :param str source: Source of a message [`human`, `ai`, `system`]. Defaults to "human".
    :param int max_size: Maximum size of the message in symbols. If exceed the limit will raise ValueError.

    :return: Langchain message object.
    :rtype: HumanMessage|AIMessage|SystemMessage
    """
    if len(message.text) > max_size:
        raise ValueError("Message is too long.")

    if message.text is None: message.text = ""
    content = [{"type": "text", "text": message.text}]

    if message.attachments:
        for image in message.attachments:
            if isinstance(image, Image):
                content.append({"type": "image_url", "image_url": {"url": await __attachment_to_content(image, pipeline.messenger_interface)}})

    if source == "human":
        return HumanMessage(content=content)
    elif source == "ai":
        return AIMessage(content=content)
    elif source == "system":
        return SystemMessage(content=content)
    else:
        raise ValueError("Invalid source name. Only `human`, `ai` and `system` are supported.")
