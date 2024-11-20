import base64
import logging

from chatsky.core.context import Context
from chatsky.core.message import Image, Message
from chatsky.llm._langchain_imports import HumanMessage, SystemMessage, AIMessage, check_langchain_available
from chatsky.llm.filters import BaseFilter


async def message_to_langchain(message: Message, ctx: Context, source: str = "human", max_size: int = 1000):
    """
    Create a langchain message from a ~chatsky.script.core.message.Message object.

    :param message: Chatsky Message to convert to Langchain Message.
    :param ctx: Current dialog context.
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

    if message.attachments:
        for image in message.attachments:
            if isinstance(image, Image):
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": await attachment_to_content(image, ctx.pipeline.messenger_interface)},
                    }
                )

    if source == "human":
        return HumanMessage(content=content)
    elif source == "ai":
        return AIMessage(content=content)
    elif source == "system":
        return SystemMessage(content=content)
    else:
        raise ValueError("Invalid source name. Only `human`, `ai` and `system` are supported.")


async def attachment_to_content(attachment: Image, iface) -> str:
    """
    Convert chatsky.Image to base64 string.
    """
    image_bytes = await attachment.get_bytes(iface)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    extension = str(attachment.source).split(".")[-1]
    if image_b64 == "" or extension is None:
        raise ValueError("Data image is not accessible.")
    image_b64 = f"data:image/{extension};base64,{image_b64}"
    return image_b64


async def context_to_history(ctx: Context, length: int, filter_func: BaseFilter, model_name: str, max_size: int) -> list:
    """
    Convert context to list of langchain messages.

    :param ctx: Current dialog context.
    :param length: Amount of turns to include in history. Set to `-1` to include all context.
    :param filter_func: Function to filter the context.
    :param model_name: name of the model from the pipeline.
    :param max_size: Maximum size of the message in symbols.

    :return: List of Langchain message objects.
    :rtype: list[HumanMessage|AIMessage|SystemMessage]
    """
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
