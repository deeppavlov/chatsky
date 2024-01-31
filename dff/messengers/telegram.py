"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""
from pathlib import Path
from tempfile import gettempdir
from typing import Callable, Optional, Sequence, Type, cast
from pydantic import FilePath

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaAnimation, InputMediaAudio, InputMediaDocument, InputMediaPhoto, InputMediaVideo, Update, Message as TelegramMessage
from telegram.ext import Application, ExtBot, MessageHandler, CallbackQueryHandler, ContextTypes
from telegram.ext.filters import ALL
from telegram._files._basemedium import _BaseMedium

from dff.messengers.common import MessengerInterface
from dff.pipeline import Pipeline
from dff.pipeline.types import PipelineRunnerFunction
from dff.script.core.context import Context
from dff.script.core.message import Animation, Audio, Button, Contact, DataAttachment, Document, Image, Invoice, Keyboard, Location, Message, Poll, PollOption, Video


class _AbstractTelegramInterface(MessengerInterface):  # pragma: no cover
    def __init__(self, token: str, download_all_attachments: bool) -> None:
        self.application = Application.builder().token(token).build()
        self.application.add_handler(MessageHandler(ALL, self.on_message))
        self.application.add_handler(CallbackQueryHandler(self.on_callback))
        self.download_all = download_all_attachments

    async def download_telegram_file(self, file: DataAttachment) -> Optional[FilePath]:  # pragma: no cover
        if file.title is not None and file.id is not None:
            file_name = Path(gettempdir()) / str(file.title)
            if not file_name.exists():
                await (await self.application.bot.get_file(file.id)).download_to_drive(file_name)
            return FilePath(file_name)
        else:
            return None

    async def _process_attachment(self, attachment: _BaseMedium, download: bool, cls: Type[DataAttachment]) -> DataAttachment:  # pragma: no cover
        data_attachment = cls(id=attachment.file_id, title=attachment.file_unique_id)
        if download:
            data_attachment.source = await self.download_telegram_file(data_attachment)
        return data_attachment

    async def extract_message_from_telegram(self, update: TelegramMessage) -> Message:  # pragma: no cover
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
            message.attachments += [await self._process_attachment(update.audio, self.download_all, Audio)]
        if update.video is not None:
            message.attachments += [await self._process_attachment(update.video, self.download_all, Video)]
        if update.animation is not None:
            message.attachments += [await self._process_attachment(update.animation, self.download_all, Animation)]
        if len(update.photo) > 0:
            message.attachments += [await self._process_attachment(picture, self.download_all, Image) for picture in update.photo]
        if update.document is not None:
            message.attachments += [await self._process_attachment(update.document, self.download_all, Document)]

        return message

    def _create_keyboard(self, buttons: Sequence[Sequence[Button]]) -> Optional[InlineKeyboardMarkup]:  # pragma: no cover
        button_list = None
        if len(buttons) > 0:
            button_list = [[InlineKeyboardButton(text=button.text, callback_data=button.data if button.data is not None else button.text) for button in row] for row in buttons]
        if button_list is None:
            return None
        else:
            return InlineKeyboardMarkup(button_list)

    async def cast_message_to_telegram_and_send(self, bot: ExtBot, chat_id: int, message: Message) -> None:  # pragma: no cover
        buttons = list()
        if message.attachments is not None:
            files = list()
            for attachment in message.attachments:
                if isinstance(attachment, Location):
                    await bot.send_location(chat_id, attachment.latitude, attachment.longitude, reply_markup=self._create_keyboard(buttons))
                    return
                if isinstance(attachment, Contact):
                    await bot.send_contact(chat_id, attachment.phone_number, attachment.first_name, attachment.last_name, reply_markup=self._create_keyboard(buttons))
                    return
                if isinstance(attachment, Poll):
                    await bot.send_poll(chat_id, attachment.question, [option.text for option in attachment.options], reply_markup=self._create_keyboard(buttons))
                    return
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
            if len(files) > 0:
                await bot.send_media_group(chat_id, files, caption=message.text)
                return
        if message.text is not None:
            await bot.send_message(chat_id, message.text, reply_markup=self._create_keyboard(buttons))

    async def on_message(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat is not None and update.message is not None:
            message = await self.extract_message_from_telegram(update.message)
            message.original_message = update
            resp = await self.callback(message, update.effective_chat.id)
            if resp.last_response is not None:
                await self.cast_message_to_telegram_and_send(self.application.bot, update.effective_chat.id, resp.last_response)

    async def on_callback(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        if update.effective_chat is not None and update.callback_query is not None:
            message = Message(text=update.callback_query.data)
            message.original_message = update
            resp = await self.callback(message, update.effective_chat.id)
            if resp.last_response is not None:
                await self.cast_message_to_telegram_and_send(self.application.bot, update.effective_chat.id, resp.last_response)

    async def connect(self, callback: PipelineRunnerFunction, *args, **kwargs):
        self.callback = callback


class PollingTelegramInterface(_AbstractTelegramInterface):  # pragma: no cover
    def __init__(self, token: str, download_all_attachments: bool = False, interval: int = 2, timeout: int = 20) -> None:
        super().__init__(token, download_all_attachments)
        self.interval = interval
        self.timeout = timeout

    async def connect(self, callback: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(callback, *args, **kwargs)
        self.application.run_polling(poll_interval=self.interval, timeout=self.timeout, allowed_updates=Update.ALL_TYPES)


class CallbackTelegramInterface(_AbstractTelegramInterface):  # pragma: no cover
    def __init__(self, token: str, download_all_attachments: bool = False, host: str = "localhost", port: int = 844):
        super().__init__(token, download_all_attachments)
        self.listen = host
        self.port = port
    
    async def connect(self, callback: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(callback, *args, **kwargs)
        self.application.run_webhook(listen=self.listen, port=self.port, allowed_updates=Update.ALL_TYPES)


def telegram_condition(func: Callable[[Update], bool]):  # pragma: no cover

    def condition(ctx: Context, _: Pipeline, *__, **___):  # pragma: no cover
        last_request = ctx.last_request
        if last_request is None or last_request.original_message is None:
            return False
        original_message = cast(Update, last_request.original_message)
        return func(original_message)

    return condition
