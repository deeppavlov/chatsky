"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""

from pathlib import Path
from typing import Callable, Optional

try:
    from telegram import (
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
        CallbackQuery,
        Contact,
        DataAttachment,
        Document,
        Image,
        Invoice,
        Location,
        Message,
        Poll,
        PollOption,
        Sticker,
        Video,
    )

    telegram_available = True
except ImportError:
    telegram_available = False


class _AbstractTelegramInterface(MessengerInterface):  # pragma: no cover
    supported_request_attachment_types = {Location, Contact, Poll, Sticker, Audio, Video, Animation, Image, Document, Invoice}
    supported_response_attachment_types = {Location, Contact, Poll, Sticker, Audio, Video, Animation, Image, Document}

    def __init__(self, token: str, attachments_directory: Optional[Path] = None) -> None:
        super().__init__(attachments_directory)
        if not telegram_available:
            raise ImportError("`python-telegram-bot` package is missing.\nTry to run `pip install dff[telegram]`.")

        self.application = Application.builder().token(token).build()
        self.application.add_handler(MessageHandler(ALL, self.on_message))
        self.application.add_handler(CallbackQueryHandler(self.on_callback))

    async def populate_attachment(self, attachment: DataAttachment) -> bytes:  # pragma: no cover
        if attachment.id is not None:
            file = await self.application.bot.get_file(attachment.id)
            data = await file.download_as_bytearray()
            return bytes(data)
        else:
            raise ValueError(f"For attachment {attachment} id is not defined!")

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
                    user_id=update.contact.user_id,
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
                    is_closed=update.poll.is_closed,
                    is_anonymous=update.poll.is_anonymous,
                    type=update.poll.type,
                    multiple_answers=update.poll.allows_multiple_answers,
                    correct_option_id=update.poll.correct_option_id,
                    explanation=update.poll.explanation,
                    open_period=update.poll.open_period,
                )
            ]
        if update.sticker is not None:
            message.attachments += [
                Sticker(
                    id=update.sticker.file_id,
                    is_animated=update.sticker.is_animated,
                    is_video=update.sticker.is_video,
                    type=update.sticker.type,
                )
            ]
        if update.audio is not None:
            thumbnail = (
                Image(id=update.audio.thumbnail.file_id, title=update.audio.thumbnail.file_unique_id)
                if update.audio.thumbnail is not None
                else None
            )
            message.attachments += [
                Audio(
                    id=update.audio.file_id,
                    title=update.audio.file_unique_id,
                    duration=update.audio.duration,
                    performer=update.audio.performer,
                    file_name=update.audio.file_name,
                    mime_type=update.audio.mime_type,
                    thumbnail=thumbnail,
                )
            ]
        if update.video is not None:
            thumbnail = (
                Image(id=update.video.thumbnail.file_id, title=update.video.thumbnail.file_unique_id)
                if update.video.thumbnail is not None
                else None
            )
            message.attachments += [
                Video(
                    id=update.video.file_id,
                    title=update.video.file_unique_id,
                    width=update.video.width,
                    height=update.video.height,
                    duration=update.video.duration,
                    file_name=update.video.file_name,
                    mime_type=update.video.mime_type,
                    thumbnail=thumbnail,
                )
            ]
        if update.animation is not None:
            thumbnail = (
                Image(id=update.animation.thumbnail.file_id, title=update.animation.thumbnail.file_unique_id)
                if update.animation.thumbnail is not None
                else None
            )
            message.attachments += [
                Animation(
                    id=update.animation.file_id,
                    title=update.animation.file_unique_id,
                    width=update.animation.width,
                    height=update.animation.height,
                    duration=update.animation.duration,
                    file_name=update.animation.file_name,
                    mime_type=update.animation.mime_type,
                    thumbnail=thumbnail,
                )
            ]
        if len(update.photo) > 0:
            message.attachments += [
                Image(
                    id=picture.file_id,
                    title=picture.file_unique_id,
                    width=picture.width,
                    height=picture.height,
                )
                for picture in update.photo
            ]
        if update.document is not None:
            thumbnail = (
                Image(id=update.document.thumbnail.file_id, title=update.document.thumbnail.file_unique_id)
                if update.document.thumbnail is not None
                else None
            )
            message.attachments += [
                Document(
                    id=update.document.file_id,
                    title=update.document.file_unique_id,
                    file_name=update.document.file_name,
                    mime_type=update.document.mime_type,
                    thumbnail=thumbnail,
                )
            ]

        return message

    async def cast_message_to_telegram_and_send(
        self, bot: ExtBot, chat_id: int, message: Message
    ) -> None:  # pragma: no cover
        if message.attachments is not None:
            files = list()
            for attachment in message.attachments:
                if isinstance(attachment, Location):
                    await bot.send_location(
                        chat_id,
                        attachment.latitude,
                        attachment.longitude,
                        horizontal_accuracy=attachment.__pydantic_extra__.get("horizontal_accuracy", None),
                        disable_notification=attachment.__pydantic_extra__.get("disable_notification", None),
                        protect_content=attachment.__pydantic_extra__.get("protect_content", None),
                        reply_markup=attachment.__pydantic_extra__.get("reply_markup", None),
                    )
                if isinstance(attachment, Contact):
                    await bot.send_contact(
                        chat_id,
                        attachment.phone_number,
                        attachment.first_name,
                        attachment.last_name,
                        vcard=attachment.__pydantic_extra__.get("vcard", None),
                        disable_notification=attachment.__pydantic_extra__.get("disable_notification", None),
                        protect_content=attachment.__pydantic_extra__.get("protect_content", None),
                        reply_markup=attachment.__pydantic_extra__.get("reply_markup", None),
                    )
                if isinstance(attachment, Poll):
                    await bot.send_poll(
                        chat_id,
                        attachment.question,
                        [option.text for option in attachment.options],
                        is_anonymous=attachment.__pydantic_extra__.get("is_anonymous", None),
                        type=attachment.__pydantic_extra__.get("type", None),
                        allows_multiple_answers=attachment.__pydantic_extra__.get("allows_multiple_answers", None),
                        correct_option_id=attachment.__pydantic_extra__.get("correct_option_id", None),
                        explanation=attachment.__pydantic_extra__.get("explanation", None),
                        explanation_parse_mode=attachment.__pydantic_extra__.get("explanation_parse_mode", None),
                        open_period=attachment.__pydantic_extra__.get("open_period", None),
                        is_closed=attachment.__pydantic_extra__.get("is_closed", None),
                        disable_notification=attachment.__pydantic_extra__.get("disable_notification", None),
                        protect_content=attachment.__pydantic_extra__.get("protect_content", None),
                        reply_markup=attachment.__pydantic_extra__.get("reply_markup", None),
                    )
                if isinstance(attachment, Sticker):
                    sticker = await attachment.get_bytes(self) if attachment.id is None else attachment.id
                    await bot.send_sticker(
                        chat_id,
                        sticker,
                        disable_notification=attachment.__pydantic_extra__.get("disable_notification", None),
                        reply_markup=attachment.__pydantic_extra__.get("reply_markup", None),
                        emoji=attachment.__pydantic_extra__.get("emoji", None),
                    )
                if isinstance(attachment, Audio):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        if len(message.attachments) > 1:
                            files += [
                                InputMediaAudio(
                                    attachment_bytes,
                                    filename=attachment.__pydantic_extra__.get("filename", None),
                                    caption=attachment.__pydantic_extra__.get("caption", None),
                                    parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                    performer=attachment.__pydantic_extra__.get("performer", None),
                                    title=attachment.__pydantic_extra__.get("title", None),
                                    thumbnail=attachment.__pydantic_extra__.get("thumbnail", None),
                                ),
                            ]
                        else:
                            await bot.send_audio(
                                chat_id,
                                audio=attachment_bytes,
                                performer=attachment.__pydantic_extra__.get("performer", None),
                                title=attachment.__pydantic_extra__.get("title", None),
                                caption=message.text,
                                disable_notification=attachment.__pydantic_extra__.get("disable_notification", None),
                                reply_markup=attachment.__pydantic_extra__.get("reply_markup", None),
                                parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                thumbnail=attachment.__pydantic_extra__.get("thumbnail", None),
                            )
                            return
                if isinstance(attachment, Video):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        if len(message.attachments) > 1:
                            files += [
                                InputMediaVideo(
                                    attachment_bytes,
                                    filename=attachment.__pydantic_extra__.get("filename", None),
                                    caption=attachment.__pydantic_extra__.get("caption", None),
                                    parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                    supports_streaming=attachment.__pydantic_extra__.get("supports_streaming", None),
                                    has_spoiler=attachment.__pydantic_extra__.get("has_spoiler", None),
                                    thumbnail=attachment.__pydantic_extra__.get("thumbnail", None),
                                ),
                            ]
                        else:
                            await bot.send_video(
                                chat_id,
                                attachment_bytes,
                                caption=message.text,
                                disable_notification=attachment.__pydantic_extra__.get("disable_notification", None),
                                reply_markup=attachment.__pydantic_extra__.get("reply_markup", None),
                                parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                supports_streaming=attachment.__pydantic_extra__.get("supports_streaming", None),
                                has_spoiler=attachment.__pydantic_extra__.get("has_spoiler", None),
                                thumbnail=attachment.__pydantic_extra__.get("thumbnail", None),
                                filename=attachment.__pydantic_extra__.get("filename", None),
                            )
                            return
                if isinstance(attachment, Animation):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        if len(message.attachments) > 1:
                            files += [
                                InputMediaAnimation(
                                    attachment_bytes,
                                    filename=attachment.__pydantic_extra__.get("filename", None),
                                    caption=attachment.__pydantic_extra__.get("caption", None),
                                    parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                    has_spoiler=attachment.__pydantic_extra__.get("has_spoiler", None),
                                    thumbnail=attachment.__pydantic_extra__.get("thumbnail", None),
                                ),
                            ]
                        else:
                            await bot.send_animation(
                                chat_id,
                                attachment_bytes,
                                caption=message.text,
                                parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                disable_notification=attachment.__pydantic_extra__.get("disable_notification", None),
                                reply_markup=attachment.__pydantic_extra__.get("reply_markup", None),
                                has_spoiler=attachment.__pydantic_extra__.get("has_spoiler", None),
                                thumbnail=attachment.__pydantic_extra__.get("thumbnail", None),
                                filename=attachment.__pydantic_extra__.get("filename", None),
                            )
                            return
                if isinstance(attachment, Image):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        if len(message.attachments) > 1:
                            files += [
                                InputMediaPhoto(
                                    attachment_bytes,
                                    filename=attachment.__pydantic_extra__.get("filename", None),
                                    caption=attachment.__pydantic_extra__.get("caption", None),
                                    parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                    has_spoiler=attachment.__pydantic_extra__.get("has_spoiler", None),
                                ),
                            ]
                        else:
                            await bot.send_photo(
                                chat_id,
                                attachment_bytes,
                                caption=message.text,
                                disable_notification=attachment.__pydantic_extra__.get("disable_notification", None),
                                reply_markup=attachment.__pydantic_extra__.get("reply_markup", None),
                                parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                has_spoiler=attachment.__pydantic_extra__.get("has_spoiler", None),
                                filename=attachment.__pydantic_extra__.get("filename", None),
                            )
                            return
                if isinstance(attachment, Document):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        if len(message.attachments) > 1:
                            files += [
                                InputMediaDocument(
                                    attachment_bytes,
                                    filename=attachment.__pydantic_extra__.get("filename", None),
                                    caption=attachment.__pydantic_extra__.get("caption", None),
                                    parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                    disable_content_type_detection=attachment.__pydantic_extra__.get(
                                        "disable_content_type_detection", None
                                    ),
                                    thumbnail=attachment.__pydantic_extra__.get("thumbnail", None),
                                ),
                            ]
                        else:
                            await bot.send_document(
                                chat_id,
                                attachment_bytes,
                                caption=message.text,
                                disable_notification=attachment.__pydantic_extra__.get("disable_notification", None),
                                reply_markup=attachment.__pydantic_extra__.get("reply_markup", None),
                                parse_mode=attachment.__pydantic_extra__.get("parse_mode", None),
                                thumbnail=attachment.__pydantic_extra__.get("thumbnail", None),
                                filename=attachment.__pydantic_extra__.get("filename", None),
                            )
                            return
            if len(files) > 0:
                await bot.send_media_group(
                    chat_id,
                    files,
                    disable_notification=message.__pydantic_extra__.get("disable_notification", None),
                    protect_content=message.__pydantic_extra__.get("protect_content", None),
                    caption=message.text,
                )
                return
        if message.text is not None:
            await bot.send_message(
                chat_id,
                message.text,
                parse_mode=message.__pydantic_extra__.get("parse_mode", None),
                disable_notification=message.__pydantic_extra__.get("disable_notification", None),
                protect_content=message.__pydantic_extra__.get("protect_content", None),
                reply_markup=message.__pydantic_extra__.get("reply_markup", None),
            )

    async def _on_event(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE, create_message: Callable[[Update], Message]
    ) -> None:
        data_available = update.message is not None or update.callback_query is not None
        if update.effective_chat is not None and data_available:
            message = create_message(update)
            message.original_message = update
            resp = await self.pipeline_runner(message, update.effective_chat.id)
            if resp.last_response is not None:
                await self.cast_message_to_telegram_and_send(
                    self.application.bot, update.effective_chat.id, resp.last_response
                )

    async def on_message(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._on_event(update, _, lambda s: self.extract_message_from_telegram(s.message))

    async def on_callback(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._on_event(update, _, lambda s: Message(attachments=[CallbackQuery(query_string=s.callback_query.data)]))

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        self.pipeline_runner = pipeline_runner
