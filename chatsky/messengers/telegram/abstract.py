"""
Telegram Base
-------------
This module implements a base interface for interactions with the
Telegram API.
"""

from pathlib import Path
from typing import Any, Callable, Optional

from chatsky.utils.devel.extra_field_helpers import grab_extra_fields

from chatsky.messengers.common import MessengerInterfaceWithAttachments
from chatsky.pipeline.types import PipelineRunnerFunction
from chatsky.script.core.message import (
    Animation,
    Audio,
    CallbackQuery,
    Contact,
    Document,
    Image,
    Invoice,
    Location,
    Message,
    Poll,
    PollOption,
    Sticker,
    Video,
    VideoMessage,
    VoiceMessage,
    MediaGroup,
)

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
    from telegram.ext import Application, ExtBot, MessageHandler, CallbackQueryHandler
    from telegram.ext.filters import ALL

    telegram_available = True
except ImportError:
    ExtBot = Any
    Update = Any
    TelegramMessage = Any

    telegram_available = False


class _AbstractTelegramInterface(MessengerInterfaceWithAttachments):
    """
    Messenger interface mixin for Telegram API usage.
    """

    supported_request_attachment_types = {
        Location,
        Contact,
        Poll,
        Sticker,
        Audio,
        Video,
        Animation,
        Image,
        Document,
        VoiceMessage,
        VideoMessage,
        Invoice,
    }
    supported_response_attachment_types = {
        Location,
        Contact,
        Poll,
        Sticker,
        Audio,
        Video,
        Animation,
        Image,
        Document,
        VoiceMessage,
        VideoMessage,
        MediaGroup,
    }

    def __init__(self, token: str, attachments_directory: Optional[Path] = None) -> None:
        super().__init__(attachments_directory)
        if not telegram_available:
            raise ImportError("`python-telegram-bot` package is missing.\nTry to run `pip install chatsky[telegram]`.")

        self.application = Application.builder().token(token).build()
        self.application.add_handler(MessageHandler(ALL, self.on_message))
        self.application.add_handler(CallbackQueryHandler(self.on_callback))

    async def get_attachment_bytes(self, source: str) -> bytes:
        file = await self.application.bot.get_file(source)
        data = await file.download_as_bytearray()
        return bytes(data)

    def extract_message_from_telegram(self, update: TelegramMessage) -> Message:
        """
        Convert Telegram update to Chatsky message.
        Extract text and supported attachments.

        :param update: Telegram update object.
        :return: Chatsky message object.
        """

        message = Message()
        message.attachments = list()

        message.text = update.text or update.caption
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
                Image(id=update.audio.thumbnail.file_id, file_unique_id=update.audio.thumbnail.file_unique_id)
                if update.audio.thumbnail is not None
                else None
            )
            message.attachments += [
                Audio(
                    id=update.audio.file_id,
                    file_unique_id=update.audio.file_unique_id,
                    duration=update.audio.duration,
                    performer=update.audio.performer,
                    file_name=update.audio.file_name,
                    mime_type=update.audio.mime_type,
                    thumbnail=thumbnail,
                )
            ]
        if update.video is not None:
            thumbnail = (
                Image(id=update.video.thumbnail.file_id, file_unique_id=update.video.thumbnail.file_unique_id)
                if update.video.thumbnail is not None
                else None
            )
            message.attachments += [
                Video(
                    id=update.video.file_id,
                    file_unique_id=update.video.file_unique_id,
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
                Image(id=update.animation.thumbnail.file_id, file_unique_id=update.animation.thumbnail.file_unique_id)
                if update.animation.thumbnail is not None
                else None
            )
            message.attachments += [
                Animation(
                    id=update.animation.file_id,
                    file_unique_id=update.animation.file_unique_id,
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
                    file_unique_id=picture.file_unique_id,
                    width=picture.width,
                    height=picture.height,
                )
                for picture in update.photo
            ]
        if update.document is not None:
            thumbnail = (
                Image(id=update.document.thumbnail.file_id, file_unique_id=update.document.thumbnail.file_unique_id)
                if update.document.thumbnail is not None
                else None
            )
            message.attachments += [
                Document(
                    id=update.document.file_id,
                    file_unique_id=update.document.file_unique_id,
                    file_name=update.document.file_name,
                    mime_type=update.document.mime_type,
                    thumbnail=thumbnail,
                )
            ]
        if update.voice is not None:
            message.attachments += [
                VoiceMessage(
                    id=update.voice.file_id,
                    file_unique_id=update.voice.file_unique_id,
                    mime_type=update.voice.mime_type,
                )
            ]
        if update.video_note is not None:
            thumbnail = (
                Image(id=update.video_note.thumbnail.file_id, file_unique_id=update.video_note.thumbnail.file_unique_id)
                if update.video_note.thumbnail is not None
                else None
            )
            message.attachments += [
                VideoMessage(
                    id=update.video_note.file_id,
                    file_unique_id=update.video_note.file_unique_id,
                    thumbnail=thumbnail,
                )
            ]

        return message

    async def cast_message_to_telegram_and_send(self, bot: ExtBot, chat_id: int, message: Message) -> None:
        """
        Send Chatsky message to Telegram.
        Sometimes, if several attachments included into message can not be sent as one update,
        several Telegram updates will be produced.
        Sometimes, if no text and none of the supported attachments are included,
        nothing will happen.

        :param bot: Telegram bot, that is used for connection to Telegram API.
        :param chat_id: Telegram dialog ID that the message will be sent to.
        :param message: Chatsky message that will be processed into Telegram updates.
        """

        if message.text is not None:
            await bot.send_message(
                chat_id,
                message.text,
                **grab_extra_fields(
                    message,
                    [
                        "parse_mode",
                        "disable_notification",
                        "protect_content",
                        "reply_markup",
                        "message_effect_id",
                        "reply_to_message_id",
                        "disable_web_page_preview",
                    ],
                ),
            )
        if message.attachments is not None:
            for attachment in message.attachments:
                if isinstance(attachment, Location):
                    await bot.send_location(
                        chat_id,
                        attachment.latitude,
                        attachment.longitude,
                        **grab_extra_fields(
                            attachment,
                            [
                                "horizontal_accuracy",
                                "disable_notification",
                                "protect_content",
                                "reply_markup",
                                "message_effect_id",
                                "reply_to_message_id",
                            ],
                        ),
                    )
                elif isinstance(attachment, Contact):
                    await bot.send_contact(
                        chat_id,
                        attachment.phone_number,
                        attachment.first_name,
                        attachment.last_name,
                        **grab_extra_fields(
                            attachment,
                            [
                                "vcard",
                                "disable_notification",
                                "protect_content",
                                "reply_markup",
                                "message_effect_id",
                                "reply_to_message_id",
                            ],
                        ),
                    )
                elif isinstance(attachment, Poll):
                    await bot.send_poll(
                        chat_id,
                        attachment.question,
                        [option.text for option in attachment.options],
                        **grab_extra_fields(
                            attachment,
                            [
                                "is_anonymous",
                                "type",
                                "allows_multiple_answers",
                                "correct_option_id",
                                "explanation",
                                "explanation_parse_mode",
                                "open_period",
                                "is_closed",
                                "disable_notification",
                                "protect_content",
                                "reply_markup",
                                "question_parse_mode",
                                "message_effect_id",
                                "reply_to_message_id",
                            ],
                        ),
                    )
                elif isinstance(attachment, Audio):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        await bot.send_audio(
                            chat_id,
                            attachment_bytes,
                            **grab_extra_fields(
                                attachment,
                                [
                                    "caption",
                                    "parse_mode",
                                    "performer",
                                    "title",
                                    "disable_notification",
                                    "protect_content",
                                    "reply_markup",
                                    "thumbnail",
                                    "message_effect_id",
                                    "reply_to_message_id",
                                    "filename",
                                ],
                            ),
                        )
                elif isinstance(attachment, Video):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        await bot.send_video(
                            chat_id,
                            attachment_bytes,
                            **grab_extra_fields(
                                attachment,
                                [
                                    "caption",
                                    "parse_mode",
                                    "supports_streaming",
                                    "disable_notification",
                                    "protect_content",
                                    "reply_markup",
                                    "has_spoiler",
                                    "thumbnail",
                                    "message_effect_id",
                                    "show_caption_above_media",
                                    "reply_to_message_id",
                                    "filename",
                                ],
                            ),
                        )
                elif isinstance(attachment, Animation):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        await bot.send_animation(
                            chat_id,
                            attachment_bytes,
                            **grab_extra_fields(
                                attachment,
                                [
                                    "caption",
                                    "parse_mode",
                                    "disable_notification",
                                    "protect_content",
                                    "reply_markup",
                                    "has_spoiler",
                                    "thumbnail",
                                    "message_effect_id",
                                    "show_caption_above_media",
                                    "reply_to_message_id",
                                    "filename",
                                ],
                            ),
                        )
                elif isinstance(attachment, Image):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        await bot.send_photo(
                            chat_id,
                            attachment_bytes,
                            **grab_extra_fields(
                                attachment,
                                [
                                    "caption",
                                    "parse_mode",
                                    "disable_notification",
                                    "protect_content",
                                    "reply_markup",
                                    "has_spoiler",
                                    "message_effect_id",
                                    "reply_to_message_id",
                                    "filename",
                                ],
                            ),
                        )
                elif isinstance(attachment, Sticker):
                    sticker = await attachment.get_bytes(self) if attachment.id is None else attachment.id
                    if sticker is not None:
                        await bot.send_sticker(
                            chat_id,
                            sticker,
                            **grab_extra_fields(
                                attachment,
                                [
                                    "emoji",
                                    "disable_notification",
                                    "protect_content",
                                    "reply_markup",
                                    "message_effect_id",
                                    "reply_to_message_id",
                                ],
                            ),
                        )
                elif isinstance(attachment, Document):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        await bot.send_document(
                            chat_id,
                            attachment_bytes,
                            **grab_extra_fields(
                                attachment,
                                [
                                    "caption",
                                    "parse_mode",
                                    "disable_notification",
                                    "protect_content",
                                    "reply_markup",
                                    "thumbnail",
                                    "message_effect_id",
                                    "reply_to_message_id",
                                    "filename",
                                ],
                            ),
                        )
                elif isinstance(attachment, VoiceMessage):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        await bot.send_voice(
                            chat_id,
                            attachment_bytes,
                            **grab_extra_fields(
                                attachment,
                                [
                                    "caption",
                                    "parse_mode",
                                    "disable_notification",
                                    "protect_content",
                                    "reply_markup",
                                    "message_effect_id",
                                    "reply_to_message_id",
                                    "filename",
                                ],
                            ),
                        )
                elif isinstance(attachment, VideoMessage):
                    attachment_bytes = await attachment.get_bytes(self)
                    if attachment_bytes is not None:
                        await bot.send_video_note(
                            chat_id,
                            attachment_bytes,
                            **grab_extra_fields(
                                attachment,
                                [
                                    "disable_notification",
                                    "protect_content",
                                    "reply_markup",
                                    "thumbnail",
                                    "message_effect_id",
                                    "reply_to_message_id",
                                    "filename",
                                ],
                            ),
                        )
                elif isinstance(attachment, MediaGroup):
                    files = list()
                    for media in attachment.group:
                        if isinstance(media, Image):
                            media_bytes = await media.get_bytes(self)
                            files += [
                                InputMediaPhoto(
                                    media_bytes,
                                    **grab_extra_fields(
                                        media,
                                        [
                                            "filename",
                                            "caption",
                                            "parse_mode",
                                            "has_spoiler",
                                            "show_caption_above_media",
                                        ],
                                    ),
                                ),
                            ]
                        elif isinstance(media, Video):
                            media_bytes = await media.get_bytes(self)
                            files += [
                                InputMediaVideo(
                                    media_bytes,
                                    **grab_extra_fields(
                                        media,
                                        [
                                            "filename",
                                            "caption",
                                            "parse_mode",
                                            "supports_streaming",
                                            "has_spoiler",
                                            "thumbnail",
                                            "show_caption_above_media",
                                        ],
                                    ),
                                ),
                            ]
                        elif isinstance(media, Animation):
                            media_bytes = await media.get_bytes(self)
                            files += [
                                InputMediaAnimation(
                                    media_bytes,
                                    **grab_extra_fields(
                                        media,
                                        [
                                            "filename",
                                            "caption",
                                            "parse_mode",
                                            "has_spoiler",
                                            "thumbnail",
                                            "show_caption_above_media",
                                        ],
                                    ),
                                ),
                            ]
                        elif isinstance(media, Audio):
                            media_bytes = await media.get_bytes(self)
                            files += [
                                InputMediaAudio(
                                    media_bytes,
                                    **grab_extra_fields(
                                        media,
                                        ["filename", "caption", "parse_mode", "performer", "title", "thumbnail"],
                                    ),
                                ),
                            ]
                        elif isinstance(media, Document):
                            media_bytes = await media.get_bytes(self)
                            files += [
                                InputMediaDocument(
                                    media_bytes,
                                    **grab_extra_fields(media, ["filename", "caption", "parse_mode", "thumbnail"]),
                                ),
                            ]
                        else:
                            raise ValueError(f"Attachment {type(media).__name__} can not be sent in a media group!")
                    await bot.send_media_group(
                        chat_id,
                        files,
                        **grab_extra_fields(
                            attachment,
                            [
                                "caption",
                                "disable_notification",
                                "protect_content",
                                "message_effect_id",
                                "reply_to_message_id",
                                "parse_mode",
                            ],
                        ),
                    )
                else:
                    raise ValueError(f"Attachment {type(attachment).__name__} is not supported!")

    async def _on_event(self, update: Update, _: Any, create_message: Callable[[Update], Message]) -> None:
        """
        Process Telegram update, run pipeline and send response to Telegram.

        :param update: Telegram update that will be processed.
        :param create_message: function that converts Telegram update to Chatsky message.
        """

        data_available = update.message is not None or update.callback_query is not None
        if update.effective_chat is not None and data_available:
            message = create_message(update)
            message.original_message = update
            resp = await self._pipeline_runner(message, update.effective_chat.id)
            if resp.last_response is not None:
                await self.cast_message_to_telegram_and_send(
                    self.application.bot, update.effective_chat.id, resp.last_response
                )

    async def on_message(self, update: Update, _: Any) -> None:
        """
        Process normal Telegram update, extracting Chatsky message from it
        using :py:meth:`~._AbstractTelegramInterface.extract_message_from_telegram`.

        :param update: Telegram update that will be processed.
        """

        await self._on_event(update, _, lambda s: self.extract_message_from_telegram(s.message))

    async def on_callback(self, update: Update, _: Any) -> None:
        """
        Process Telegram callback update, creating empty Chatsky message
        with only one callback query attachment from `callback_query.data` field.

        :param update: Telegram update that will be processed.
        """

        await self._on_event(
            update, _, lambda s: Message(attachments=[CallbackQuery(query_string=s.callback_query.data)])
        )

    async def connect(self, pipeline_runner: PipelineRunnerFunction, *args, **kwargs):
        self._pipeline_runner = pipeline_runner
