"""
LLM responses.
---------
Wrapper around langchain.
"""

try:
    from langchain_openai import ChatOpenAI

    # from langchain_anthropic import ChatAnthropic
    # from langchain_google_vertexai import ChatVertexAI
    # from langchain_cohere import ChatCohere
    # from langchain_mistralai import ChatMistralAI
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from langchain_core.output_parsers import StrOutputParser

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

try:
    from deepeval.models import DeepEvalBaseLLM

    deepeval_available = True
except ImportError:
    deepeval_available = False


class LLM_API(DeepEvalBaseLLM):
    """
    This class acts as a wrapper for all LLMs from langchain
    and handles message exchange between remote model and chatsky classes.
    """

    def __init__(
        self,
        model: ChatOpenAI,
        system_prompt: str = "",
    ) -> None:
        """
        :param model: Model object.
        :param system_prompt: System prompt for the model.
        """
        self.__check_imports()
        self.model: ChatOpenAI = model
        self.name = ""
        self.parser = StrOutputParser()
        self.system_prompt = system_prompt

    def __check_imports(self):
        if not langchain_available:
            raise ImportError("Langchain is not available. Please install it with `pip install chatsky[llm]`.")
        if not deepeval_available:
            raise ImportError("DeepEval is not available. Please install it with `pip install chatsky[llm]`.")

    def respond(
        self, history: list = [""], message_schema: Union[None, Type[Message], Type[BaseModel]] = None
    ) -> Message:
        if message_schema is None:
            result = self.parser.invoke(self.model.invoke(history))
            result = Message(text=result)

        elif issubclass(message_schema, Message):
            # Case if the message_schema desribes Message structure
            structured_model = self.model.with_structured_output(message_schema)
            result = Message.model_validate(structured_model.invoke(history))
        elif issubclass(message_schema, BaseModel):
            # Case if the message_schema desribes Message.text structure
            structured_model = self.model.with_structured_output(message_schema)
            result = structured_model.invoke(history)
            result = Message(text=str(result.json()))

        if result.annotations:
            result.annotations["__generated_by_model__"] = self.name
        else:
            result.annotations = {"__generated_by_model__": self.name}
        return result

    def condition(self, prompt: str, method: BaseMethod):
        def process_input(ctx: Context, _: Pipeline) -> bool:
            result = method(ctx, self.parser.invoke(self.model.invoke([prompt + "\n" + ctx.last_request.text])))
            return result

        return process_input

    # Helper functions for DeepEval custom LLM usage
    def generate(self, prompt: str):
        return self.model.invoke(prompt).content

    async def a_generate(self, prompt: str):
        return self.generate(prompt)

    def load_model(self):
        return self.model

    def get_model_name(self):
        return self.name


def llm_response(model_name: str, prompt: str = "", history: int = 5, filter_func: Callable = lambda *args: True):
    """
    Basic function for receiving LLM responses.
    :param ctx: Context object. (Assigned automatically)
    :param pipeline: Pipeline object. (Assigned automatically)
    :param model_name: Name of the model from the `Pipeline.models` dictionary.
    :param prompt: Prompt for the model.
    :param history: Number of messages to keep in history. `-1` for full history.
    :param filter_func: filter function to filter messages that will go the models context.
    """

    def wrapped(ctx: Context, pipeline: Pipeline) -> Message:
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
                history_messages.append(SystemMessage(node_prompt))
            if "global_prompt" in current_misc:
                global_prompt = current_misc["global_prompt"]
                history_messages.append(SystemMessage(global_prompt))
            if "local_prompt" in current_misc:
                local_prompt = current_misc["local_prompt"]
                history_messages.append(SystemMessage(local_prompt))

        # iterate over context to retrieve history messages
        if not (history == 0 or len(ctx.responses) == 0 or len(ctx.requests) == 0):
            pairs = zip(
                [ctx.requests[x] for x in range(len(ctx.requests))],
                [ctx.responses[x] for x in range(len(ctx.responses))],
            )
            if history != -1:
                for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)[-history:]):
                    history_messages.append(message_to_langchain(req))
                    history_messages.append(message_to_langchain(resp, source="ai"))
            else:
                # TODO: Fix redundant code
                for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)):
                    history_messages.append(message_to_langchain(req))
                    history_messages.append(message_to_langchain(resp, source="ai"))

        history_messages.append(SystemMessage(prompt))
        history_messages.append(message_to_langchain(ctx.last_request, source="human"))
        return model.respond(history_messages)

    return wrapped


def llm_condition(model_name: str, prompt: str, method: BaseMethod):
    """
    Basic function for using LLM in condition cases.
    :param model_name: Key of the model from the `Pipeline.models` dictionary.
    :param prompt: Prompt for the model to use on users input.
    :param method: Method that takes models output and returns boolean.
    """

    def wrapped(ctx, pipeline):
        model = pipeline.models[model_name]
        return model.condition(prompt, method)

    return wrapped


def __attachment_to_content(attachment: Image, iface) -> str:
    """
    Helper function to convert image to base64 string.
    """
    image_b64 = base64.b64encode(attachment.get_bytes(iface)).decode("utf-8")
    extension = attachment.source.split(".")[-1]
    if image_b64 == "" or extension is None:
        raise ValueError("Data image is not accessible.")
    image_b64 = f"data:image/{extension};base64,{image_b64}"
    return image_b64


def message_to_langchain(message: Message, source: str = "human"):
    """
    Creates a langchain message from a ~chatsky.script.core.message.Message object.

    Args:
        message (Message): ~chatsky.script.core.message.Message object.
        source (str, optional): Source of a message [`human`, `ai`, `system`]. Defaults to "human".

    Returns:
        HumanMessage|AIMessage|SystemMessage: langchain message object.
    """
    content = [{"type": "text", "text": message.text}]

    if message.attachments:
        for image in message.attachments:
            if isinstance(image, Image):
                content.append({"type": "image_url", "image_url": {"url": __attachment_to_content(image)}})

    if source == "human":
        return HumanMessage(content=content)
    elif source == "ai":
        return AIMessage(content=content)
    elif source == "system":
        return SystemMessage(content=content)
    else:
        raise ValueError("Invalid source name. Only `human`, `ai` and `system` are supported.")
