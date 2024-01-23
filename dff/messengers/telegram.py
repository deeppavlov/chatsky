"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""
from typing import Optional, Sequence
from pydantic import HttpUrl

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaAnimation, InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo, Update, Message as TelegramMessage
from telegram.ext import Application, MessageHandler, ContextTypes
from telegram.ext.filters import ALL

from dff.messengers.common import MessengerInterface
from dff.pipeline.types import PipelineRunnerFunction
from dff.script.core.message import Animation, Audio, Contact, Document, Image, Invoice, Keyboard, Location, Message, Poll, PollOption, Video


def extract_message_from_telegram(update: TelegramMessage) -> Message:  # pragma: no cover
    message = Message()
    message.attachments = list()

    if update.text is not None:
        message.text = update.text
    if update.location is not None:
        message.attachments += [Location(latitude=update.location.latitude, longitude=update.location.longitude)]
    if update.contact is not None:
        message.attachments += [Contact(phone_number=update.contact.phone_number, first_name=update.contact.first_name, last_name=update.contact.last_name)]
    if update.invoice is not None:
        message.attachments += [Invoice(title=update.invoice.title, description=update.invoice.description, currency=update.invoice.currency, amount=update.invoice.total_amount)]
    if update.poll is not None:
        message.attachments += [Poll(question=update.poll.question, options=[PollOption(text=option.text, votes=option.voter_count) for option in update.poll.options])]
    if update.audio is not None:
        message.attachments += [Audio(source=HttpUrl(update.audio.file_id))]
    if update.video is not None:
        message.attachments += [Video(source=HttpUrl(update.video.file_id))]
    if update.animation is not None:
        message.attachments += [Animation(source=HttpUrl(update.animation.file_id))]
    if len(update.photo) > 0:
        message.attachments += [Image(source=HttpUrl(photo.file_id)) for photo in update.photo]
    if update.document is not None:
        message.attachments += [Document(source=HttpUrl(update.document.file_id))]

    message.original_message = update
    return message


def _create_keyboard(buttons: Sequence[Sequence[str]]) -> Optional[InlineKeyboardMarkup]:
    button_list = None
    if len(buttons) > 0:
        button_list = [[InlineKeyboardButton(button) for button in row] for row in buttons]
    if button_list is None:
        return None
    else:
        return InlineKeyboardMarkup(button_list)


async def cast_message_to_telegram_and_send(update: TelegramMessage, message: Message) -> None:  # pragma: no cover
    buttons = list()
    if message.attachments is not None:
        files = list()
        for attachment in message.attachments:
            if isinstance(attachment, Location):
                await update.reply_location(attachment.latitude, attachment.longitude, reply_markup=_create_keyboard(buttons))
            if isinstance(attachment, Contact):
                await update.reply_contact(attachment.phone_number, attachment.first_name, attachment.last_name, reply_markup=_create_keyboard(buttons))
            if isinstance(attachment, Poll):
                await update.reply_poll(attachment.question, [option.text for option in attachment.options], reply_markup=_create_keyboard(buttons))
            if isinstance(attachment, Audio):
                attachment_bytes = attachment.get_bytes()
                if attachment_bytes is not None:
                    files += [InputMediaAudio(attachment_bytes)]
            if isinstance(attachment, Video):
                attachment_bytes = attachment.get_bytes()
                if attachment_bytes is not None:
                    files += [InputMediaVideo(attachment_bytes)]
            if isinstance(attachment, Animation):
                attachment_bytes = attachment.get_bytes()
                if attachment_bytes is not None:
                    files += [InputMediaAnimation(attachment_bytes)]
            if isinstance(attachment, Image):
                attachment_bytes = attachment.get_bytes()
                if attachment_bytes is not None:
                    files += [InputMediaPhoto(attachment_bytes)]
            if isinstance(attachment, Document):
                attachment_bytes = attachment.get_bytes()
                if attachment_bytes is not None:
                    files += [InputMediaDocument(attachment_bytes)]
            if isinstance(attachment, Keyboard):
                buttons = attachment.buttons
        if len(files > 0):
            await update.reply_media_group(files, caption=message.text)
    elif message.text is not None:
        await update.reply_text(message.text, reply_markup=_create_keyboard(buttons))


class AbstractTelegramInterface(MessengerInterface):  # pragma: no cover
    def __init__(self, token: str) -> None:
        self.application = Application.builder().token(token).build()
        self.application.add_handler(MessageHandler(ALL, self.on_message))

    async def on_message(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_user is not None and update.message is not None:
            message = extract_message_from_telegram(update.message)
            resp = self.callback(message, update.effective_user.id)
            if resp.last_response is not None:
                await cast_message_to_telegram_and_send(update.message, resp.last_response)

    async def connect(self, callback: PipelineRunnerFunction, *args, **kwargs):
        self.callback = callback


class PollingTelegramInterface(AbstractTelegramInterface):  # pragma: no cover
    def __init__(self, token: str, interval: int = 2, timeout: int = 20) -> None:
        super().__init__(token)
        self.interval = interval
        self.timeout = timeout

    async def connect(self, callback: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(callback, *args, **kwargs)
        self.application.run_polling(poll_interval=self.interval, timeout=self.timeout, allowed_updates=Update.ALL_TYPES)


class CallbackTelegramInterface(AbstractTelegramInterface):  # pragma: no cover
    def __init__(self, token: str, host: str = "localhost", port: int = 844):
        super().__init__(token)
        self.listen = host
        self.port = port
    
    async def connect(self, callback: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(callback, *args, **kwargs)
        self.application.run_webhook(listen=self.listen, port=self.port, allowed_updates=Update.ALL_TYPES)
