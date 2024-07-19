"""
OpenAI responses.
---------
Wrapper around langchain.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser

from chatsky.script import Message, Context

class OpenAIResponse:
    """
    This class acts as a wrapper over OpenaAI models.
    and handles message exchange between remote model and chatsky classes.
    """
    def __init__(self, model: str, api_key: str, base_url: str="", system_prompt: str="") -> None:
        """
        :param model: Name of the model.
        :param api_key: Token required for the models usage.
        :param base_url: URL of a proxy service to access the model.
        """
        self.model = ChatOpenAI(model=model, api_key=api_key, base_url=base_url)
        self.parser = StrOutputParser()
        self.messages = []
        if system_prompt != "":
            self.messages.append(SystemMessage(content=system_prompt))

    def respond(self, input: Message, ctx: Context) -> Message:
        self.messages.append(HumanMessage(input.text))
        result = self.parser.invoke(self.model.invoke(self.messages))
        self.messages.append(SystemMessage(result))

        return Message(text=result)
