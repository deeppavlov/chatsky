from typing import Optional, Any
from pydantic import HttpUrl

from whatsapp import WhatsApp, Message as WhatsAppMessage

from dff.script.core.message import Message, Audio, Video, Image, Document, Attachments
from dff.messengers.common import CallbackMessengerInterface
from dff.pipeline.types import PipelineRunnerFunction


def extract_message_from_whatsapp(message: WhatsAppMessage) -> Message:  # pragma: no cover
    inn_mess = Message()
    inn_mess.text = message.content

    if message.type == "audio":
        files = [Audio(source=HttpUrl(message.audio["id"]))]
    elif message.type == "video":
        files = [Video(source=HttpUrl(message.video["id"]))]
    elif message.type == "image":
        files = [Image(source=HttpUrl(message.image["id"]))]
    elif message.type == "document":
        files = [Document(source=HttpUrl(message.document["id"]))]
    else:
        files = list()

    inn_mess.attachments = Attachments(files=files)
    return inn_mess


def cast_message_to_whatsapp_and_send(messenger: WhatsApp, to: Any, message: Message) -> None:  # pragma: no cover
    if message.attachments is not None:
        attachment = next(message.attachments.files)
        is_link = isinstance(attachment.source, HttpUrl)
        if is_link:
            media_id = attachment.source
        else:
            media_id = messenger.upload_media(media=attachment.source)["id"]
        if isinstance(attachment, Audio):
            messenger.send_audio(audio=media_id, recipient_id=to, link=is_link)
        elif isinstance(attachment, Video):
            messenger.send_video(video=media_id, recipient_id=to, caption=message.text, link=is_link) 
        elif isinstance(attachment, Image):
            messenger.send_image(image=media_id, recipient_id=to, caption=message.text, link=is_link)
        elif isinstance(attachment, Document):
            messenger.send_document(document=media_id, recipient_id=to, caption=message.text, link=is_link)
    else:
        reply = messenger.create_message(content=message.text, to=to)
        reply.send(True)


class WhatsappInterface(CallbackMessengerInterface):  # pragma: no cover
    def __init__(
        self,
        token: str,
        phone_number_id: str,
        host: str = "localhost",
        port: int = 8443,
        debug: Optional[bool] = None,
        messenger: Optional[WhatsApp] = None,
        **wsgi_options,
    ) -> None:
        self.host = host
        self.port = port
        self.debug = debug if debug is not None else False
        self.messenger = messenger if messenger is not None else WhatsApp(token, phone_number_id, self.debug)
        self.wsgi_options = wsgi_options
        self.messenger.on_message(self.on_message)

    async def on_message(self, message: WhatsAppMessage):
        message.mark_as_read()
        resp = await self.on_request_async(extract_message_from_whatsapp(message), message.sender)
        cast_message_to_whatsapp_and_send(self.messenger, message.sender, resp.last_response)


    async def connect(self, callback: PipelineRunnerFunction):
        await super().connect(callback)
        self.messenger.run(host=self.host, port=self.port, debug=self.debug, **self.wsgi_options)
