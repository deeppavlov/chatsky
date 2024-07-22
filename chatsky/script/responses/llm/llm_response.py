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

from chatsky.script import Message, Context
from chatsky.pipeline import Pipeline

from pydantic import BaseModel
from typing import Union


class LLMResponse(BaseModel):
    """
    This class acts as a wrapper over OpenaAI models.
    and handles message exchange between remote model and chatsky classes.
    """
    def __init__(self, model: Union[ChatOpenAI, ChatAnthropic, ChatVertexAI, ChatCohere, ChatMistralAI], system_prompt: str="") -> None:
        """
        :param model: Model object.
        :param system_prompt: System prompt for the model.
        """
        self.model = model
        self.parser = StrOutputParser()
        self.messages = []
        if system_prompt != "":
            self.messages.append(SystemMessage(content=system_prompt))


    def respond(self, prompt: str=""):
        def inner_response(ctx: Context, _: Pipeline) -> Message:
            self.messages.append(HumanMessage(prompt + '\n' + ctx.last_request.text))
            result = self.parser.invoke(self.model.invoke(self.messages))
            self.messages.append(SystemMessage(result))
            return Message(text=result)
        return inner_response
