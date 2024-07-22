"""
LLM responses.
---------
Wrapper around langchain.
"""

try:
    from langchain_openai import ChatOpenAI
    open_ai_available = True
except ImportError:
    open_ai_available = False

try:
    from langchain_anthropic import ChatAnthropic
    anthropic_available = True
except ImportError:
    anthropic_available = False

try:
    from langchain_google_vertexai import ChatVertexAI
    vertex_ai_available = True
except ImportError:
    vertex_ai_available = False

try:
    from langchain_cohere import ChatCohere
    cohere_available = True
except ImportError:
    cohere_available = False

try:
    from langchain_mistralai import ChatMistralAI
    mistral_available = True
except ImportError:
    mistral_available = False

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

import base64
import httpx

from chatsky.script import Message, Context
from chatsky.pipeline import Pipeline

from pydantic import BaseModel
from typing import Union, Callable


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
        if not open_ai_available:
            raise ImportError("OpenAI is not available. Please install it with `pip install langchain-openai`.")  
        if not anthropic_available:
            raise ImportError("Anthropic is not available. Please install it with `pip install langchain-anthropic`.")
        if not vertex_ai_available:
            raise ImportError("Vertex AI is not available. Please install it with `pip install langchain-google-vertexai`.")
        if not cohere_available:
            raise ImportError("Cohere is not available. Please install it with `pip install langchain-cohere`.")
        if not mistral_available:
            raise ImportError("Mistral is not available. Please install it with `pip install langchain-mistralai`.")
        

    def respond(self, history: int = []) -> Message:
        result = self.parser.invoke(self.model.invoke(history))
        result = Message(text=result)
        result.annotation.__generated_by_model__ = self.name
        return result
    
    def condition(self, prompt=None, method="bool"):
        raise NotImplementedError("Condition is not implemented.")


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
                    image_source = image.source
                    if "http" in image_source:
                        image_data = httpx.get(image_source).content
                    else:
                        with open(image_source, "rb") as image_file:
                            image_data = image_file.read()
                    image_b64 = base64.b64encode(image_data).decode("utf-8")
                    extension = image_source.split(".")[-1]
                    image_b64 = f"data:image/{extension};base64,{image_b64}"
                    content.append(
                        {"type": "image_url", "image_url": {"url": image_b64}}
                    )
                req_message = HumanMessage(content=content)
            else:
                req_message = HumanMessage(req.text)

            history_messages.append(req_message)
            history_messages.append(SystemMessage(resp.text))
    return model.respond(history_messages)