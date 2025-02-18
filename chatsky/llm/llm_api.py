"""
LLM responses.
--------------
Wrapper around langchain.
"""

from typing import Union, Type
import logging

from pydantic import BaseModel, TypeAdapter

from chatsky.core.message import Message
from chatsky.llm.methods import BaseMethod
from chatsky.llm.prompt import PositionConfig
from chatsky.core import AnyResponse, MessageInitTypes
from chatsky.llm._langchain_imports import StrOutputParser, BaseChatModel, BaseMessage, check_langchain_available


logger = logging.getLogger(__name__)


class LLM_API:
    """
    This class acts as a wrapper for all LLMs from langchain
    and handles message exchange between remote model and chatsky classes.
    """

    def __init__(
        self,
        model: BaseChatModel,
        system_prompt: Union[AnyResponse, MessageInitTypes] = "",
        position_config: PositionConfig = None,
    ) -> None:
        """
        :param model: Model object
        :param system_prompt: System prompt for the model
        """
        check_langchain_available()
        self.model: BaseChatModel = model
        self.parser = StrOutputParser()
        self.system_prompt = TypeAdapter(AnyResponse).validate_python(system_prompt)
        self.position_config = position_config or PositionConfig()

    async def respond(
        self,
        history: list[BaseMessage],
        message_schema: Union[None, Type[Message], Type[BaseModel]] = None,
    ) -> Message:
        """
        Process and structure the model's response based on the provided schema.

        :param history: List of previous messages in the conversation
        :param message_schema: Schema for structuring the output, defaults to None
        :return: Processed model response

        :raises ValueError: If message_schema is not None, Message, or BaseModel
        """

        if message_schema is None:
            result = await self.parser.ainvoke(await self.model.ainvoke(history))
            return Message(text=result)
        elif issubclass(message_schema, Message):
            # Case if the message_schema describes Message structure
            structured_model = self.model.with_structured_output(message_schema, method="json_mode")
            model_result = await structured_model.ainvoke(history)
            logger.debug(f"Generated response: {model_result}")
            return Message.model_validate(model_result)
        elif issubclass(message_schema, BaseModel):
            # Case if the message_schema describes Message.text structure
            structured_model = self.model.with_structured_output(message_schema)
            model_result = await structured_model.ainvoke(history)
            return Message(text=message_schema.model_validate(model_result).model_dump_json())
        else:
            raise ValueError

    async def condition(self, history: list[BaseMessage], method: BaseMethod) -> bool:
        """
        Execute a conditional method on the conversation history.

        :param history: List of previous messages in the conversation
        :param method: Method to evaluate the condition

        :return: Boolean result of the condition evaluation
        """
        result = await method(history, await self.model.agenerate([history], logprobs=True, top_logprobs=10))
        return result
