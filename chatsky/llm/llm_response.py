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
    langchain_available = True
except ImportError:
    langchain_available = False

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

import base64
import httpx

from chatsky.script.core.message import Image, Message
from chatsky.script import Context
from chatsky.pipeline import Pipeline

from pydantic import BaseModel
from typing import Union

import re


class LLM_API(BaseModel):
    """
    This class acts as a wrapper for all LLMs from langchain
    and handles message exchange between remote model and chatsky classes.
    """

    def __init__(
        self,
        model: Union[
            ChatOpenAI, ChatAnthropic, ChatVertexAI, ChatCohere, ChatMistralAI
        ],
        system_prompt: str = "",
    ) -> None:
        """
        :param model: Model object.
        :param system_prompt: System prompt for the model.
        """
        self.__check_imports()
        self.model = model
        self.name = ""
        self.parser = StrOutputParser()
        self.system_prompt = system_prompt


    def __check_imports(self):
        if not langchain_available:
            raise ImportError("Langchain is not available. Please install it with `pip install chatsky[llm]`.")
        

    def respond(self, history: list = []) -> Message:
        result = self.parser.invoke(self.model.invoke(history))
        result = Message(text=result)
        result.annotation.__generated_by_model__ = self.name
        return result
    
    def condition(self, prompt, request):
        result = self.parser.invoke(self.model.invoke([prompt+'\n'+request.text]))
        return result


def llm_response(
        ctx: Context,
        pipeline: Pipeline,
        model_name,
        prompt="",
        history=10,
        filter_non_llm=True
    ):
    """
    Basic function for receiving LLM responses.
    :param ctx: Context object. (Assigned automatically)
    :param pipeline: Pipeline object. (Assigned automatically)
    :param model_name: Name of the model from the `Pipeline.models` dictionary.
    :param prompt: Prompt for the model.
    :param history: Number of messages to keep in history.
    :param filter_non_llm: Whether to filter non-LLM messages from the history.
    """
    model = pipeline.get(model_name)
    history_messages = []
    if history == 0:
        return model.respond([prompt + "\n" + ctx.last_request.text])
    else:
        for req, resp in zip(ctx.requests[-history:], ctx.responses[-history:]):
            if filter_non_llm and resp.annotation.__generated_by_model__ != model_name:
                continue
            if req.attachments != []:
                content = [{"type": "text", "text": prompt + "\n" + ctx.last_request.text}]
                for image in ctx.last_request.attachments:
                    if image is not Image:
                        continue
                    content.append(
                        {"type": "image_url", "image_url": {"url": __attachment_to_content(image)}}
                    )
                req_message = HumanMessage(content=content)
            else:
                req_message = HumanMessage(req.text)

            history_messages.append(req_message)
            history_messages.append(SystemMessage(resp.text))
        return model.respond(history_messages)


def llm_condition(
        ctx: Context,
        pipeline: Pipeline,
        model_name,
        prompt="",
        method="regex",
        threshold=0.9
    ):
    """
    Basic function for using LLM in condition cases.
    """
    model = pipeline.get(model_name)
    if method == "regex":
        return re.match(r"True", model.condition(prompt, ctx.last_request))


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


def message_to_langchain(message: Message):
    if message.attachments != []:
        content = [{"type": "text", "text": message.text}]
        for image in message.attachments:
            if image is not Image:
                continue
            content.append(
                {"type": "image_url", "image_url": {"url": __attachment_to_content(image)}}
            )
    return HumanMessage(content=content)