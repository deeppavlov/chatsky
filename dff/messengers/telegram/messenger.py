"""
Messenger
-----------------
The Messenger module provides the :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger` class.
The former inherits from the :py:class:`~TeleBot` class from the `pytelegrambotapi` library.
Using it, you can put Telegram update handlers inside your script and condition your transitions accordingly.

"""
from pathlib import Path
from typing import Union, List, Optional, Callable

from telebot import types, TeleBot

from dff.script import Context, Actor

from .utils import partialmethod, batch_open_io
from .message import TelegramMessage, TelegramUI, RemoveKeyboard

from dff.script import Message
from dff.script.core.message import Audio, Video, Image, Document


class TelegramMessenger(TeleBot):
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
        self.cnd = TelegramConditions(self)

    def send_response(self, chat_id: Union[str, int], response: Union[str, dict, Message]) -> None:
        """
        Cast `response` to :py:class:`~dff.messengers.telegram.types.TelegramMessage` and send it.
        Text content is sent after all the attachments.

        :param chat_id: Telegram chat ID.
        :param response: Response data. String, dictionary or :py:class:`~dff.script.responses.generics.Response`.
            will be cast to :py:class:`~dff.messengers.telegram.types.TelegramMessage`.
        """
        if isinstance(response, TelegramMessage):
            ready_response = response
        elif isinstance(response, str):
            ready_response = TelegramMessage(text=response)
        elif isinstance(response, dict) or isinstance(response, Message):
            ready_response = TelegramMessage.parse_obj(response)
        else:
            raise TypeError(
                "Type of the response argument should be one of the following:"
                " `str`, `dict`, `Message`, or `TelegramMessage`."
            )
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
                params = {"caption": attachment.title}
                if isinstance(attachment.source, Path):
                    with open(attachment.source, "rb") as file:
                        method(chat_id, file, **params)
                else:
                    method(chat_id, attachment.source or attachment.id, **params)
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
                    return cast_to_media_type(media=file.source or file.id, caption=file.title)

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
                    buttons = [types.InlineKeyboardButton(
                        text=item.text,
                        url=item.source,
                        callback_data=item.payload,
                    ) for item in ready_response.ui.buttons]
                else:
                    keyboard = types.ReplyKeyboardMarkup(row_width=ready_response.ui.row_width)
                    buttons = [types.KeyboardButton(
                        text=item.text,
                    ) for item in ready_response.ui.buttons]
                keyboard.add(*buttons, row_width=ready_response.ui.row_width)
            else:
                keyboard = ready_response.ui
        else:
            keyboard = None

        self.send_message(
            chat_id=chat_id,
            text=ready_response.text,
            reply_markup=keyboard,
        )


class TelegramConditions:
    """
    This class includes methods that produce :py:class:`~dff.script.core.script.Script`
    conditions based on `pytelegrambotapi` updates.

    It is included to the :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
    as :py:attr:`cnd` attribute on instantiation.

    To set a condition in your script, stick to the signature of the original :py:class:`~TeleBot` methods.
    E.g. the result of

    .. code-block:: python

        messenger.cnd.message_handler(func=lambda msg: True)

    in your :py:class:`~dff.script.core.script.Script` will always be `True`,
    unless the new update is not a message.

    :param messenger: Messenger instance.

    """

    def __init__(self, messenger: TelegramMessenger):
        self.messenger = messenger

    def handler(
        self,
        target_type: type,
        commands: Optional[List[str]] = None,
        regexp: Optional[str] = None,
        func: Optional[Callable] = None,
        content_types: Optional[List[str]] = None,
        chat_types: Optional[List[str]] = None,
        **kwargs,
    ):
        """
        Creates a condition triggered by updates that match the given parameters.
        The signature is equal with the `Telebot` method of the same name.

        :param commands: Telegram command trigger. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_.
        :param regexp: Regex trigger. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_.
        :param func: Callable trigger. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_.
        :param content_types: Content type trigger. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_.
        :param chat_types: Chat type trigger. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_.
        """

        update_handler = self.messenger._build_handler_dict(
            None,
            False,
            commands=commands,
            regexp=regexp,
            func=func,
            content_types=content_types,
            chat_types=chat_types,
            **kwargs,
        )

        def condition(ctx: Context, actor: Actor, *args, **kwargs):
            last_request = ctx.last_request
            if last_request is None or last_request.misc is None:
                return False
            update = last_request.misc.get("update")
            if not update or not isinstance(update, target_type):
                return False
            test_result = self.messenger._test_message_handler(update_handler, update)
            return test_result

        return condition

    message_handler = partialmethod(handler, target_type=types.Message)

    edited_message_handler = partialmethod(handler, target_type=types.Message)

    channel_post_handler = partialmethod(handler, target_type=types.Message)

    edited_channel_post_handler = partialmethod(handler, target_type=types.Message)

    inline_handler = partialmethod(handler, target_type=types.InlineQuery)

    chosen_inline_handler = partialmethod(handler, target_type=types.ChosenInlineResult)

    callback_query_handler = partialmethod(handler, target_type=types.CallbackQuery)

    shipping_query_handler = partialmethod(handler, target_type=types.ShippingQuery)

    pre_checkout_query_handler = partialmethod(handler, target_type=types.PreCheckoutQuery)

    poll_handler = partialmethod(handler, target_type=types.Poll)

    poll_answer_handler = partialmethod(handler, target_type=types.PollAnswer)

    chat_member_handler = partialmethod(handler, target_type=types.ChatMemberUpdated)

    my_chat_member_handler = partialmethod(handler, target_type=types.ChatMemberUpdated)

    chat_join_request_handler = partialmethod(handler, target_type=types.ChatJoinRequest)
