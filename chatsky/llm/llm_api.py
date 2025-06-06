"""
LLM responses.
--------------
Wrapper around langchain.
"""

from typing import Union, Type, Optional
import logging

from pydantic import BaseModel, TypeAdapter, Field

from chatsky import Context
from chatsky.core.message import Message
from chatsky.llm.methods import BaseMethod
from chatsky.llm.prompt import PositionConfig, Prompt
from chatsky.core import AnyResponse, MessageInitTypes
from chatsky.llm.filters import BaseHistoryFilter, DefaultFilter
from chatsky.llm.langchain_context import get_langchain_context
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


class BaseLLMScriptFunction(BaseModel):
    """
    Base class for script functions that use an LLM model.
    """

    llm_model_name: str
    """
    Key of the model in the :py:attr:`~chatsky.core.pipeline.Pipeline.models` dictionary.
    """
    prompt: Prompt = Field(default="", validate_default=True)
    """
    Script function prompt.
    """
    history: int = 1
    """
    Number of dialogue turns aside from the current one to keep in history. `-1` for full history.
    """
    filter_func: BaseHistoryFilter = Field(default_factory=DefaultFilter)
    """
    Filter function to filter messages in history.
    """
    prompt_misc_filter: str = Field(default=r"prompt")
    """
    Regular expression to find prompts by key names in MISC dictionary.
    """
    position_config: Optional[PositionConfig] = None
    """
    Config for positions of prompts and messages in history.
    """
    max_size: int = 5000
    """
    Maximum size of any message in chat in symbols.
    If a message exceeds the limit it will not be sent to the LLM and a warning
    will be produced.
    """

    async def _get_langchain_context(self, ctx: Context) -> list[BaseMessage]:
        """
        Convert :py:class:`Context` to langchain messages using :py:func:`.get_langchain_context`.

        Arguments to the function are passed from attributes of this class and from
        the :py:class:`.LLM_API` model stored in pipeline:

        1. Model is retrieved from pipeline using :py:attr:`llm_model_name`;
        2. Model's ``system_prompt`` is executed and passed to :py:func:`.get_langchain_context` as ``system_prompt``;
        3. If :py:attr:`position_config` is `None`, model's ``position_config`` is used instead;
        4. The rest of the arguments are passed as is.

        :param ctx: Context object.
        :return: A list of LangChain messages.
        """
        model = self._get_api(ctx=ctx)

        return await get_langchain_context(
            system_prompt=await model.system_prompt(ctx),
            ctx=ctx,
            call_prompt=self.prompt,
            prompt_misc_filter=self.prompt_misc_filter,
            position_config=self.position_config or model.position_config,
            length=self.history,
            filter_func=self.filter_func,
            llm_model_name=self.llm_model_name,
            max_size=self.max_size,
        )

    def _get_api(self, ctx: Context) -> LLM_API:
        """
        Get LLM_API instance for the current model.

        :param ctx: Context object
        :return: LLM_API instance
        """
        model = ctx.pipeline.models[self.llm_model_name]
        return model
