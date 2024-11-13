import base64
from chatsky.core.context import Context
from chatsky.core.message import Image, Message
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


async def message_to_langchain(message: Message, ctx: Context, source: str = "human", max_size: int = 1000):
    """
    Creates a langchain message from a ~chatsky.script.core.message.Message object.

    :param Message message: ~chatsky.script.core.message.Message object.
    :param Pipeline pipeline: ~chatsky.pipeline.Pipeline object.
    :param str source: Source of a message [`human`, `ai`, `system`]. Defaults to "human".
    :param int max_size: Maximum size of the message in symbols. 
    If exceed the limit will raise ValueError. Is not affected by system prompt size.

    :return: Langchain message object.
    :rtype: HumanMessage|AIMessage|SystemMessage
    """
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
                        "image_url": {"url": await __attachment_to_content(image, ctx.pipeline.messenger_interface)},
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


async def __attachment_to_content(attachment: Image, iface) -> str:
    """
    Helper function to convert image to base64 string.
    """
    image_bytes = await attachment.get_bytes(iface)
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    extension = str(attachment.source).split(".")[-1]
    if image_b64 == "" or extension is None:
        raise ValueError("Data image is not accessible.")
    image_b64 = f"data:image/{extension};base64,{image_b64}"
    return image_b64
