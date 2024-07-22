"""
OpenAI responses.
---------
Wrapper around langchain.
"""

# TODO: I do not like downloading all the models just to use it in Union.
# It also requires different packages like `langchain-mistralai`, `langchain-openai` etc.
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_vertexai import ChatVertexAI
from langchain_cohere import ChatCohere
from langchain_mistralai import ChatMistralAI

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

import base64
import httpx

from chatsky.script import Message, Context
from chatsky.pipeline import Pipeline

from pydantic import BaseModel
from typing import Union


class LLMResponse(BaseModel):
    """
    This class acts as a wrapper over OpenaAI models.
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
        self.model = model
        self.parser = StrOutputParser()
        self.messages = []
        if system_prompt != "":
            self.messages.append(SystemMessage(content=system_prompt))

    def respond(self, prompt: str = ""):
        def inner_response(ctx: Context, _: Pipeline) -> Message:
            if ctx.last_request.attachments != []:
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

                message = HumanMessage(content=content)
            else:
                message = HumanMessage(prompt + "\n" + ctx.last_request.text)
            self.messages.append(message)
            result = self.parser.invoke(self.model.invoke(self.messages))
            self.messages.append(SystemMessage(result))
            return Message(text=result)

        return inner_response
