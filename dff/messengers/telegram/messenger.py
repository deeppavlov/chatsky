"""
Messenger
-----------------
The Messenger module provides the :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger` class.
The former inherits from the :py:class:`~TeleBot` class from the `pytelegrambotapi` library.
Using it, you can put Telegram update handlers inside your script and condition your transitions accordingly.

"""
from pathlib import Path
from typing import Union, List, Optional, Callable
from enum import Enum

from telebot import types, TeleBot

from dff.script import Context
from dff.pipeline import Pipeline

from .utils import batch_open_io
from .message import TelegramMessage, TelegramUI, RemoveKeyboard

from dff.script import Message
from dff.script.core.message import Audio, Video, Image, Document


class TelegramMessenger(TeleBot):  # pragma: no cover
    """
    This class inherits from `Telebot` and implements framework-specific functionality
    like sending generic responses.

    :param token: A Telegram API bot token.
    :param kwargs: Arbitrary parameters that match the signature of the `Telebot` class.
        For reference see: `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_ .

    """

    def __init__(
        self,
        token: str,
        **kwargs,
    ):
        super().__init__(token, threaded=False, **kwargs)

    def send_response(self, chat_id: Union[str, int], response: Union[str, dict, Message]) -> None:
        """
        Cast `response` to :py:class:`~dff.messengers.telegram.types.TelegramMessage` and send it.
        Message fields are sent in separate messages in the following order:

        1. Attachments
        2. Location
        3. Text with keyboard

        :param chat_id: Telegram chat ID.
        :param response: Response data. String, dictionary or :py:class:`~dff.script.responses.generics.Response`.
            will be cast to :py:class:`~dff.messengers.telegram.types.TelegramMessage`.
        """
        if isinstance(response, TelegramMessage):
            ready_response = response
        elif isinstance(response, str):
            ready_response = TelegramMessage(text=response)
        elif isinstance(response, Message):
            ready_response = TelegramMessage.model_validate(response.model_dump())
        elif isinstance(response, dict):
            ready_response = TelegramMessage.model_validate(response)
        else:
            raise TypeError(
                "Type of the response argument should be one of the following:"
                " `str`, `dict`, `Message`, or `TelegramMessage`."
            )
        parse_mode = ready_response.parse_mode.value if ready_response.parse_mode is not None else None
        if ready_response.attachments is not None:
            if len(ready_response.attachments.files) == 1:
                attachment = ready_response.attachments.files[0]
                if isinstance(attachment, Audio):
                    method = self.send_audio
                elif isinstance(attachment, Document):
                    method = self.send_document
                elif isinstance(attachment, Video):
                    method = self.send_video
                elif isinstance(attachment, Image):
                    method = self.send_photo
                else:
                    raise TypeError(type(attachment))
                params = {"caption": attachment.title, "parse_mode": parse_mode}
                if isinstance(attachment.source, Path):
                    with open(attachment.source, "rb") as file:
                        method(chat_id, file, **params)
                else:
                    method(chat_id, str(attachment.source or attachment.id), **params)
            else:

                def cast(file):
                    if isinstance(file, Image):
                        cast_to_media_type = types.InputMediaPhoto
                    elif isinstance(file, Audio):
                        cast_to_media_type = types.InputMediaAudio
                    elif isinstance(file, Document):
                        cast_to_media_type = types.InputMediaDocument
                    elif isinstance(file, Video):
                        cast_to_media_type = types.InputMediaVideo
                    else:
                        raise TypeError(type(file))
                    return cast_to_media_type(media=str(file.source or file.id), caption=file.title)

                files = map(cast, ready_response.attachments.files)
                with batch_open_io(files) as media:
                    self.send_media_group(chat_id=chat_id, media=media)

        if ready_response.location:
            self.send_location(
                chat_id=chat_id,
                latitude=ready_response.location.latitude,
                longitude=ready_response.location.longitude,
            )

        if ready_response.ui is not None:
            if isinstance(ready_response.ui, RemoveKeyboard):
                keyboard = types.ReplyKeyboardRemove()
            elif isinstance(ready_response.ui, TelegramUI):
                if ready_response.ui.is_inline:
                    keyboard = types.InlineKeyboardMarkup(row_width=ready_response.ui.row_width)
                    buttons = [
                        types.InlineKeyboardButton(
                            text=item.text,
                            url=item.source,
                            callback_data=item.payload,
                        )
                        for item in ready_response.ui.buttons
                    ]
                else:
                    keyboard = types.ReplyKeyboardMarkup(row_width=ready_response.ui.row_width)
                    buttons = [
                        types.KeyboardButton(
                            text=item.text,
                        )
                        for item in ready_response.ui.buttons
                    ]
                keyboard.add(*buttons, row_width=ready_response.ui.row_width)
            else:
                keyboard = ready_response.ui
        else:
            keyboard = None

        if ready_response.text is not None:
            self.send_message(
                chat_id=chat_id,
                text=ready_response.text,
                reply_markup=keyboard,
                parse_mode=parse_mode,
            )
        elif keyboard is not None:
            self.send_message(
                chat_id=chat_id,
                text="",
                reply_markup=keyboard,
                parse_mode=parse_mode,
            )


_default_messenger = TeleBot("")


class UpdateType(Enum):
    """
    Represents a type of the telegram update
    (which field contains an update in :py:class:`telebot.types.Update`).
    See `link <https://pytba.readthedocs.io/en/latest/types.html#telebot.types.Update>`__.
    """

    ALL = "ALL"
    MESSAGE = "message"
    EDITED_MESSAGE = "edited_message"
    CHANNEL_POST = "channel_post"
    EDITED_CHANNEL_POST = "edited_channel_post"
    INLINE_QUERY = "inline_query"
    CHOSEN_INLINE_RESULT = "chosen_inline_result"
    CALLBACK_QUERY = "callback_query"
    SHIPPING_QUERY = "shipping_query"
    PRE_CHECKOUT_QUERY = "pre_checkout_query"
    POLL = "poll"
    POLL_ANSWER = "poll_answer"
    MY_CHAT_MEMBER = "my_chat_member"
    CHAT_MEMBER = "chat_member"
    CHAT_JOIN_REQUEST = "chat_join_request"


def telegram_condition(
    messenger: TeleBot = _default_messenger,
    update_type: UpdateType = UpdateType.MESSAGE,
    commands: Optional[List[str]] = None,
    regexp: Optional[str] = None,
    func: Optional[Callable] = None,
    content_types: Optional[List[str]] = None,
    chat_types: Optional[List[str]] = None,
    **kwargs,
):
    """
    A condition triggered by updates that match the given parameters.

    :param messenger:
        Messenger to test filters on. Used only for :py:attr:`Telebot.custom_filters`.
        Defaults to :py:data:`._default_messenger`.
    :param update_type:
        If set to any `UpdateType` other than `UpdateType.ALL`
        it will check that an update is of the same type.
        Defaults to `UpdateType.Message`.
    :param commands:
        Telegram command trigger.
        See `link <https://github.com/eternnoir/pyTelegramBotAPI#general-api-documentation>`__.
    :param regexp:
        Regex trigger.
        See `link <https://github.com/eternnoir/pyTelegramBotAPI#general-api-documentation>`__.
    :param func:
        Callable trigger.
        See `link <https://github.com/eternnoir/pyTelegramBotAPI#general-api-documentation>`__.
    :param content_types:
        Content type trigger.
        See `link <https://github.com/eternnoir/pyTelegramBotAPI#general-api-documentation>`__.
    :param chat_types:
        Chat type trigger.
        See `link <https://github.com/eternnoir/pyTelegramBotAPI#general-api-documentation>`__.
    """

    update_handler = messenger._build_handler_dict(
        None,
        False,
        commands=commands,
        regexp=regexp,
        func=func,
        content_types=content_types,
        chat_types=chat_types,
        **kwargs,
    )

    def condition(ctx: Context, _: Pipeline, *__, **___):  # pragma: no cover
        last_request = ctx.last_request
        if last_request is None:
            return False
        update = getattr(last_request, "update", None)
        request_update_type = getattr(last_request, "update_type", None)
        if update is None:
            return False
        if update_type != UpdateType.ALL and request_update_type != update_type.value:
            return False
        test_result = messenger._test_message_handler(update_handler, update)
        return test_result

    return condition
