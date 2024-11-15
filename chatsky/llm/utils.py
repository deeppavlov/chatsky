import logging

from chatsky.core.context import Context
from chatsky.core.message import Message
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage, check_langchain_available


async def message_to_langchain(message: Message, ctx: Context, source: str = "human", max_size: int = 1000):
    """
    Creates a langchain message from a ~chatsky.script.core.message.Message object.

    :param message: Chatsky Message to convert to Langchain Message.
    :param ctx: Context the message belongs to.
    :param source: Source of a message [`human`, `ai`, `system`]. Defaults to "human".
    :param max_size: Maximum size of the message in symbols.
        If exceed the limit will raise ValueError. Is not affected by system prompt size.

    :return: Langchain message object.
    :rtype: HumanMessage|AIMessage|SystemMessage
    """
    check_langchain_available()
    if len(message.text) > max_size:
        raise ValueError("Message is too long.")

    if message.text is None:
        message.text = ""
    content = [{"type": "text", "text": message.text}]

    if source == "human":
        return HumanMessage(content=content)
    elif source == "ai":
        return AIMessage(content=content)
    elif source == "system":
        return SystemMessage(content=content)
    else:
        raise ValueError("Invalid source name. Only `human`, `ai` and `system` are supported.")


async def context_to_history(ctx: Context, length: int, filter_func, model_name: str, max_size: int):

    history = []

    pairs = zip(
        [ctx.requests[x] for x in range(1, len(ctx.requests) + 1)],
        [ctx.responses[x] for x in range(1, len(ctx.responses) + 1)],
    )
    logging.debug(f"Dialogue turns: {pairs}")
    if length != -1:
        for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)[-length:]):
            logging.debug(f"This pair is valid: {req, resp}")
            history.append(await message_to_langchain(req, ctx=ctx, max_size=max_size))
            history.append(await message_to_langchain(resp, ctx=ctx, source="ai", max_size=max_size))
    else:
        # TODO: Fix redundant code
        for req, resp in filter(lambda x: filter_func(ctx, x[0], x[1], model_name), list(pairs)):
            logging.debug(f"This pair is valid: {req, resp}")
            history.append(await message_to_langchain(req, ctx=ctx, max_size=max_size))
            history.append(await message_to_langchain(resp, ctx=ctx, source="ai", max_size=max_size))
    return history
