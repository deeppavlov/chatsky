"""
LLM Utils.
----------
The Utils module contains functions for converting Chatsky's objects to an LLM_API and langchain compatible versions.
"""
import logging
from typing import Literal, Union
import asyncio

from chatsky.core import Context, Message
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage, check_langchain_available
from chatsky.llm.filters import BaseHistoryFilter, Return


logger = logging.getLogger(__name__)


async def message_to_langchain(
    message: Message, ctx: Context, source: Literal["human", "ai", "system"] = "human", max_size: int = 5000
) -> Union[HumanMessage, AIMessage, SystemMessage]:
    """
    Create a langchain message from a :py:class:`~chatsky.script.core.message.Message` object.

    :param message: Chatsky Message to convert to Langchain Message.
    :param ctx: Current dialog context.
    :param source: Source of the message [`human`, `ai`, `system`]. Defaults to "human".
    :param max_size: Maximum size of the message measured in characters.
        If a message exceeds the limit it will not be sent to the LLM and a warning
        will be produced
    """
    check_langchain_available()
    if message.text is None:
        content = []
    elif len(message.text) > max_size:
        logger.warning("Message is too long.")
        content = []
    else:
        content = [{"type": "text", "text": message.text}]

    if source == "human":
        return HumanMessage(content=content)
    elif source == "ai":
        return AIMessage(content=content)
    elif source == "system":
        return SystemMessage(content=content)
    else:
        return HumanMessage(content=content)


async def context_to_history(
    ctx: Context, length: int, filter_func: BaseHistoryFilter, llm_model_name: str, max_size: int
) -> list[Union[HumanMessage, AIMessage, SystemMessage]]:
    """
    Convert context to list of langchain messages.

    :param ctx: Current dialog context.
    :param length: Amount of turns to include in history. Set to `-1` to include all context.
    :param filter_func: Function to filter the context.
    :param llm_model_name: name of the model from the pipeline.
    :param max_size: Maximum size of the message in symbols.

    :return: List of Langchain message objects.
    """
    check_langchain_available()
    history = []
    indices = list(range(1, ctx.current_turn_id))

    if length == 0:
        return []
    elif length > 0:
        indices = indices[-length:]

    for request, response in zip(*await asyncio.gather(ctx.requests.get(indices), ctx.responses.get(indices))):
        filter_result = filter_func(ctx, request, response, llm_model_name)
        if request is not None and filter_result in (Return.Request, Return.Turn):
            history.append(await message_to_langchain(request, ctx=ctx, max_size=max_size))
        if response is not None and filter_result in (Return.Response, Return.Turn):
            history.append(await message_to_langchain(response, ctx=ctx, source="ai", max_size=max_size))

    return history
