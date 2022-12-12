"""
Messenger
-----------------
The Messenger module provides the :py:class:`~dff.connectors.messenger.telegram.messenger.TelegramMessenger` class.
The former inherits from the :py:class:`~TeleBot` class from the `pytelegrambotapi` library.
Using it, you can put Telegram update handlers inside your script and condition your transitions accordingly.

"""
from pathlib import Path
from typing import Union, List, Optional, Callable

from telebot import types, TeleBot

from dff.core.engine.core import Context, Actor

from .utils import partialmethod, open_io, close_io
from .types import TelegramResponse

from dff.connectors.messenger.generics import Response
from dff.connectors.messenger.telegram.utils import TELEGRAM_STATE_KEY


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
        self.cnd: TelegramConditions = TelegramConditions(self)

    def send_response(self, chat_id: Union[str, int], response: Union[str, dict, Response, TelegramResponse]) -> None:
        """
        Cast `response` to :py:class:`~dff.connectors.messenger.telegram.types.TelegramResponse` and send it.
        Text content is sent after all the attachments.

        :param chat_id: Telegram chat ID.
        :param response: Response data. String, dictionary or :py:class:`~dff.connectors.messenger.generics.Response`.
            will be cast to :py:class:`~dff.connectors.messenger.telegram.types.TelegramResponse`.
        """
        if isinstance(response, TelegramResponse):
            ready_response = response
        elif isinstance(response, str):
            ready_response = TelegramResponse(text=response)
        elif isinstance(response, dict) or isinstance(response, Response):
            ready_response = TelegramResponse.parse_obj(response)
        else:
            raise TypeError(
                "Type of the response argument should be one of the following:"
                " `str`, `dict`, `Response`, or `TelegramResponse`."
            )

        for attachment_prop, method in [
            (ready_response.image, self.send_photo),
            (ready_response.video, self.send_video),
            (ready_response.document, self.send_document),
            (ready_response.audio, self.send_audio),
        ]:
            if attachment_prop is None:
                continue
            params = {"caption": attachment_prop.title}
            if isinstance(attachment_prop.source, Path):
                with open(attachment_prop.source, "rb") as file:
                    method(chat_id, file, **params)
            else:
                method(chat_id, attachment_prop.source or attachment_prop.id, **params)

        if ready_response.location:
            self.send_location(
                chat_id=chat_id,
                latitude=ready_response.location.latitude,
                longitude=ready_response.location.longitude,
            )

        if ready_response.attachments:
            opened_media = [open_io(item) for item in ready_response.attachments.files]
            self.send_media_group(chat_id=chat_id, media=opened_media)
            for item in opened_media:
                close_io(item)

        self.send_message(
            chat_id=chat_id,
            text=ready_response.text,
            reply_markup=ready_response.ui and ready_response.ui.keyboard,
        )


class TelegramConditions:
    """
    This class includes methods that produce `Script` conditions based on `pytelegrambotapi` updates.

    It is included to the :py:class:`~dff.connectors.messenger.telegram.messenger.TelegramMessenger`
    as :py:attr:`cnd` attribute on instantiation.

    To set a condition in your script, stick to the signature of the original :py:class:`~TeleBot` methods.
    E. g. the result of

    .. code-block:: python

        messenger.cnd.message_handler(func=lambda msg: True)

    in your :py:class:`~dff.core.engine.core.Script` will always be `True`, unless the new update is not a message.

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
            update = ctx.framework_states.get(TELEGRAM_STATE_KEY, {}).get("data")
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
