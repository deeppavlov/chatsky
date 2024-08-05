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
    from langchain.output_parsers import ResponseSchema, StructuredOutputParser
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    from langchain_core.output_parsers import StrOutputParser
    langchain_available = True
except ImportError:
    langchain_available = False

import base64
import httpx
import re

from chatsky.script.core.message import Image, Message
from chatsky.script import Context
from chatsky.pipeline import Pipeline
from chatsky.llm.methods import BaseMethod

from pydantic import BaseModel
from typing import Union, Callable

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
        

    def respond(self, history: list = [""], message_schema=None) -> Message:
        result = self.parser.invoke(self.model.invoke(history))
        result = Message(text=result)
        # result.annotation.__generated_by_model__ = self.name
        return result
    
    def condition(self, prompt: str, method: BaseMethod):
        def process_input(ctx: Context, _: Pipeline) -> bool:
            result = method(ctx, self.parser.invoke(self.model.invoke([prompt+'\n'+ctx.last_request.text])))
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


def llm_response(
        model_name,
        prompt="",
        history=5,
        filter_func: Callable=lambda x: True
    ):
    """
    Basic function for receiving LLM responses.
    :param ctx: Context object. (Assigned automatically)
    :param pipeline: Pipeline object. (Assigned automatically)
    :param model_name: Name of the model from the `Pipeline.models` dictionary.
    :param prompt: Prompt for the model.
    :param history: Number of messages to keep in history.
    :param filter_func: filter function to filter messages that will go the models context.
    """
    def wrapped(ctx: Context, pipeline: Pipeline):
        model = pipeline.models[model_name]
        if model.system_prompt == "":
            history_messages = []
        else:
            history_messages = [SystemMessage(model.system_prompt)]
        if history == 0:
            return model.respond(history_messages+[prompt + "\n" + ctx.last_request.text])
        else:
            pairs = zip([ctx.requests[x] for x in range(len(ctx.requests))],
                     [ctx.responses[x] for x in range(len(ctx.responses))])
            for req, resp in filter(lambda x: filter_func(x), list(pairs)[-history:]):
                history_messages.append(message_to_langchain(req))
                history_messages.append(message_to_langchain(resp, human=False))
            history_messages.append(message_to_langchain(ctx.last_request, prompt=prompt))    
            print(history_messages)
            return model.respond(history_messages)
    return wrapped

def llm_condition(
        model_name: str,
        prompt: str,
        method: BaseMethod
    ):
    """
    Basic function for using LLM in condition cases.
    """
    def wrapped(ctx, pipeline):
        model = pipeline.models[model_name]
        return model.condition(prompt, method)
    return wrapped


def __attachment_to_content(attachment: Image) -> str:
    """
    Helper function to convert image to base64 string.
    """
    if "http" in attachment.source:
        image_data = httpx.get(attachment.source).content
    else:
        with open(attachment.source, "rb") as image_file:
            image_data = image_file.read()
    image_b64 = base64.b64encode(image_data).decode("utf-8")
    extension = attachment.source.split(".")[-1]
    image_b64 = f"data:image/{extension};base64,{image_b64}"
    return image_b64


def message_to_langchain(message: Message, prompt: str= "", human: bool=True):
    content = [{"type": "text", "text": prompt + "\n" + message.text}]
    if message.attachments:
        for image in message.attachments:
            if image is not Image:
                continue
            content.append(
                {"type": "image_url", "image_url": {"url": __attachment_to_content(image)}}
            )
    if human:
        return HumanMessage(content=content)
    else:
        return AIMessage(content=content)
