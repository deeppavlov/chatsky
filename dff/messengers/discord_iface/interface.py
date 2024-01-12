from io import BytesIO
from logging import getLogger

from discord import Intents, Client, File, Message as DiscordMessage
from discord.abc import Messageable
from pydantic import HttpUrl

from dff.messengers.common import CallbackMessengerInterface
from dff.pipeline.types import PipelineRunnerFunction
from dff.script.core.message import Attachments, Audio, Document, Image, Message, Video

logger = getLogger(__name__)


def extract_message_from_discord(message: DiscordMessage) -> Message:  # pragma: no cover
    inn_mess = Message()
    inn_mess.text = message.content

    files = list()
    if len(message.attachments) > 0:
        first_attachment = message.attachments[0]
        if first_attachment.content_type is not None:
            content_type = first_attachment.content_type.split("/")[0]
            if content_type == "audio":
                files = [Audio(source=HttpUrl(first_attachment.url))]
            elif content_type == "video":
                files = [Video(source=HttpUrl(first_attachment.url))]
            elif content_type == "image":
                files = [Image(source=HttpUrl(first_attachment.url))]
            elif content_type in ("application", "text"):
                files = [Document(source=HttpUrl(first_attachment.url))]

    inn_mess.attachments = Attachments(files=files)
    return inn_mess


async def cast_message_to_discord_and_send(channel: Messageable, message: Message) -> None:  # pragma: no cover
    files = list()
    if message.attachments is not None:
        for file in message.attachments.files[:10]:
            if file.source is not None:
                files += [File(BytesIO(file.get_bytes()), file.title)]

    await channel.send(message.text, files=files)


class DiscordInterface(CallbackMessengerInterface):
    def __init__(self, token: str) -> None:
        self._token = token

        intents = Intents.default()
        intents.message_content = True
        self._client = Client(intents=intents)
        self._client.event(self.on_message)

    async def on_message(self, message: DiscordMessage):
        if message.author != self._client.user:
            resp = await self.on_request_async(extract_message_from_discord(message), message.author.id)
            await cast_message_to_discord_and_send(message.channel, resp.last_response)

    async def connect(self, callback: PipelineRunnerFunction):
        await super().connect(callback)
        await self._client.login(self._token)
        await self._client.connect()
