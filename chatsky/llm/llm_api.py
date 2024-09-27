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
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.language_models.chat_models import BaseChatModel

    langchain_available = True
except ImportError:
    langchain_available = False


from chatsky.core.message import Message
from chatsky.core.context import Context
from chatsky.core.pipeline import Pipeline
from chatsky.llm.methods import BaseMethod

from typing import Union, Callable, Type, Optional
from pydantic import BaseModel

from chatsky.llm.utils import message_to_langchain


class LLM_API:
    """
    This class acts as a wrapper for all LLMs from langchain
    and handles message exchange between remote model and chatsky classes.
    """

    def __init__(
        self,
        model: BaseChatModel,
        system_prompt: Optional[str] = "",
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
            structured_model = self.model.with_structured_output(message_schema)
            result = Message.model_validate(await structured_model.ainvoke(history))
        elif issubclass(message_schema, BaseModel):
            # Case if the message_schema desribes Message.text structure
            structured_model = self.model.with_structured_output(message_schema)
            result = await structured_model.ainvoke(history)
            result = Message(text=str(result))

        if result.annotations:
            result.annotations["__generated_by_model__"] = self.name
        else:
            result.annotations = {"__generated_by_model__": self.name}
        return result

    async def condition(self, prompt: str, method: BaseMethod, return_schema=None):
        async def process_input(ctx: Context, _: Pipeline) -> bool:
            condition_history = [
                await message_to_langchain(Message(prompt), pipeline=_, source="system"),
                await message_to_langchain(ctx.last_request, pipeline=_, source="human"),
            ]
            result = method(ctx, await self.model.agenerate([condition_history], logprobs=True, top_logprobs=10))
            return result

        return process_input
