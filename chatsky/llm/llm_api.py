"""
LLM responses.
--------------
Wrapper around langchain.
"""

from typing import Union, Type, Optional
from pydantic import BaseModel
import logging
from chatsky.core.message import Message
from chatsky.core.context import Context
from chatsky.llm.methods import BaseMethod
from chatsky.llm.utils import message_to_langchain
from chatsky.llm._langchain_imports import StrOutputParser, BaseChatModel, BaseMessage, check_langchain_available


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
        check_langchain_available()
        self.model: BaseChatModel = model
        self.parser = StrOutputParser()
        self.system_prompt = system_prompt

    async def respond(
        self,
        history: list[BaseMessage],
        message_schema: Union[None, Type[Message], Type[BaseModel]] = None,
    ) -> Message:

        if message_schema is None:
            result = await self.parser.ainvoke(await self.model.ainvoke(history))
            return Message(text=result)
        elif issubclass(message_schema, Message):
            # Case if the message_schema describes Message structure
            structured_model = self.model.with_structured_output(message_schema, method="json_mode")
            model_result = await structured_model.ainvoke(history)
            logging.debug(f"Generated response: {model_result}")
            return Message.model_validate(model_result)
        elif issubclass(message_schema, BaseModel):
            # Case if the message_schema describes Message.text structure
            structured_model = self.model.with_structured_output(message_schema)
            model_result = await structured_model.ainvoke(history)
            return Message(text=message_schema.model_validate(model_result).model_dump_json())
        else:
            raise ValueError

    async def condition(
        self, history: list[BaseMessage], method: BaseMethod, return_schema: Optional[BaseModel] = None
    ) -> bool:
        result = await method(history, await self.model.agenerate([history], logprobs=True, top_logprobs=10))
        return result
