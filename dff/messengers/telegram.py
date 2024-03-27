"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""

from pathlib import Path
from tempfile import gettempdir
from typing import Callable, Optional, Sequence
from pydantic import FilePath

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Update,
    Message as TelegramMessage,
)
from telegram.ext import Application, ExtBot, MessageHandler, CallbackQueryHandler, ContextTypes
from telegram.ext.filters import ALL

from dff.messengers.common import MessengerInterface
from dff.pipeline.types import PipelineRunnerFunction
from dff.script.core.message import (
    Animation,
    Audio,
    Button,
    CallbackQuery,
    Contact,
    DataAttachment,
    Document,
    Image,
    Invoice,
    Keyboard,
    Location,
    Message,
    Poll,
    PollOption,
    Video,
)


class _AbstractTelegramInterface(MessengerInterface):  # pragma: no cover
    request_attachments = {Location, Contact, Invoice, Poll, Audio, Video, Animation, Image, Document}
    response_attachments = {Location, Contact, Poll, Audio, Video, Animation, Image, Document, Keyboard}

    def __init__(self, token: str) -> None:
        self.application = Application.builder().token(token).build()
        self.application.add_handler(MessageHandler(ALL, self.on_message))
        self.application.add_handler(CallbackQueryHandler(self.on_callback))

    async def populate_attachment(self, attachment: DataAttachment) -> None:  # pragma: no cover
        if attachment.title is not None and attachment.id is not None:
            file_name = Path(gettempdir()) / str(attachment.title)
            if not file_name.exists():
                await (await self.application.bot.get_file(attachment.id)).download_to_drive(file_name)
            attachment.source = FilePath(file_name)
        else:
            raise ValueError(f"For attachment {attachment} title or id is not defined!")

    def extract_message_from_telegram(self, update: TelegramMessage) -> Message:  # pragma: no cover
        message = Message()
        message.attachments = list()

        if update.text is not None:
            message.text = update.text
        if update.location is not None:
            message.attachments += [Location(latitude=update.location.latitude, longitude=update.location.longitude)]
        if update.contact is not None:
            message.attachments += [
                Contact(
                    phone_number=update.contact.phone_number,
                    first_name=update.contact.first_name,
                    last_name=update.contact.last_name,
                )
            ]
        if update.invoice is not None:
            message.attachments += [
                Invoice(
                    title=update.invoice.title,
                    description=update.invoice.description,
                    currency=update.invoice.currency,
                    amount=update.invoice.total_amount,
                )
            ]
        if update.poll is not None:
            message.attachments += [
                Poll(
                    question=update.poll.question,
                    options=[PollOption(text=option.text, votes=option.voter_count) for option in update.poll.options],
                )
            ]
        if update.audio is not None:
            message.attachments += [
                Audio(id=update.audio.file_id, title=update.audio.file_unique_id, from_messenger_interface=self)
            ]
        if update.video is not None:
            message.attachments += [
                Video(id=update.video.file_id, title=update.video.file_unique_id, from_messenger_interface=self)
            ]
        if update.animation is not None:
            message.attachments += [
                Animation(
                    id=update.animation.file_id, title=update.animation.file_unique_id, from_messenger_interface=self
                )
            ]
        if len(update.photo) > 0:
            message.attachments += [
                Image(id=picture.file_id, title=picture.file_unique_id, from_messenger_interface=self)
                for picture in update.photo
            ]
        if update.document is not None:
            message.attachments += [
                Document(
                    id=update.document.file_id, title=update.document.file_unique_id, from_messenger_interface=self
                )
            ]

        return message

    def _create_keyboard(
        self, buttons: Sequence[Sequence[Button]]
    ) -> Optional[InlineKeyboardMarkup]:  # pragma: no cover
        button_list = None
        if len(buttons) > 0:
            button_list = [
                [
                    InlineKeyboardButton(
                        text=button.text, callback_data=button.data if button.data is not None else button.text
                    )
                    for button in row
                ]
                for row in buttons
            ]
        if button_list is None:
            return None
        else:
            return InlineKeyboardMarkup(button_list)

    async def cast_message_to_telegram_and_send(
        self, bot: ExtBot, chat_id: int, message: Message
    ) -> None:  # pragma: no cover
        buttons = list()
        if message.attachments is not None:
            files = list()
            for attachment in message.attachments:
                if isinstance(attachment, Location):
                    await bot.send_location(
                        chat_id, attachment.latitude, attachment.longitude, reply_markup=self._create_keyboard(buttons)
                    )
                if isinstance(attachment, Contact):
                    await bot.send_contact(
                        chat_id,
                        attachment.phone_number,
                        attachment.first_name,
                        attachment.last_name,
                        reply_markup=self._create_keyboard(buttons),
                    )
                if isinstance(attachment, Poll):
                    await bot.send_poll(
                        chat_id,
                        attachment.question,
                        [option.text for option in attachment.options],
                        reply_markup=self._create_keyboard(buttons),
                    )
                if isinstance(attachment, Audio):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        files += [InputMediaAudio(attachment_bytes)]
                if isinstance(attachment, Video):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        files += [InputMediaVideo(attachment_bytes)]
                if isinstance(attachment, Animation):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        files += [InputMediaAnimation(attachment_bytes)]
                if isinstance(attachment, Image):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        files += [InputMediaPhoto(attachment_bytes)]
                if isinstance(attachment, Document):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        files += [InputMediaDocument(attachment_bytes)]
                if isinstance(attachment, Keyboard):
                    buttons = attachment.buttons
            if len(files) > 0:
                await bot.send_media_group(chat_id, files, caption=message.text)
                return
        if message.text is not None:
            await bot.send_message(chat_id, message.text, reply_markup=self._create_keyboard(buttons))

    async def _on_event(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE, create_message: Callable[[Update], Message]
    ) -> None:
        if update.effective_chat is not None and update.message is not None:
            message = create_message(update)
            message.original_message = update
            resp = await self.callback(message, update.effective_chat.id)
            if resp.last_response is not None:
                await self.cast_message_to_telegram_and_send(
                    self.application.bot, update.effective_chat.id, resp.last_response
                )

    async def on_message(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._on_event(update, _, lambda u: self.extract_message_from_telegram(u.message))

    async def on_callback(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._on_event(
            update, _, lambda u: Message(attachments=[CallbackQuery(query_string=u.callback_query.data)])
        )

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        self.callback = pipeline_runner


class PollingTelegramInterface(_AbstractTelegramInterface):  # pragma: no cover
    def __init__(self, token: str, interval: int = 2, timeout: int = 20) -> None:
        super().__init__(token)
        self.interval = interval
        self.timeout = timeout

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(pipeline_runner, *args, **kwargs)
        self.application.run_polling(
            poll_interval=self.interval, timeout=self.timeout, allowed_updates=Update.ALL_TYPES
        )


class CallbackTelegramInterface(_AbstractTelegramInterface):  # pragma: no cover
    def __init__(self, token: str, host: str = "localhost", port: int = 844):
        super().__init__(token)
        self.listen = host
        self.port = port

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        await super().connect(pipeline_runner, *args, **kwargs)
        self.application.run_webhook(listen=self.listen, port=self.port, allowed_updates=Update.ALL_TYPES)
