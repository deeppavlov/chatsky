"""
Connector
-----------------

| The Connector module provides the :py:class:`~df_telegram_connector.connector.TelegramConnector` class.
| The former inherits from the :py:class:`~telebot.TeleBot` class from the :py:mod:`~pytelegrambotapi` library.
| Using it, you can put Telegram update handlers inside your script and condition your transitions accordingly.

"""
from pathlib import Path
from typing import Union

from telebot import types, TeleBot

from dff.core.engine.core import Context, Actor

from .utils import partialmethod, open_io, close_io
from .types import TelegramResponse

import dff.connectors.messenger.generics


class TelegramConnector(TeleBot):
    """
    This class inherits from `Telebot` and implements dff-specific functionality, including script conditions
    and sending generic responses.

    Parameters
    ----------

    token: str
        A Telegram API bot token.
    threaded: bool
        This parameter is currently deprecated for the sake of compatibility with `dff.core.runner`.
        We plan to add support for the threaded polling mode in the future.
    args:
        The rest of the parameters exactly matches those of the `Telebot` class. See the pytelegrambotapi docs
        for more info: `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_ .

    """

    def __init__(self, token, threaded=False, parse_mode=None, skip_pending=False, *args, **kwargs):
        super().__init__(token, threaded=False, parse_mode=parse_mode, skip_pending=skip_pending, *args, **kwargs)
        self.cnd = ConditionNamespace(self)

    def send_response(
        self, chat_id: Union[str, int], response: Union[str, dict, dff.connectors.messenger.generics.Response, TelegramResponse]
    ):
        """
        Cast the `response` argument to the :py:class:`~df_telegram_connector.types.TelegramResponse` type and send it.
        The order is that the media are sent first, after which the marked-up text message is sent.

        Parameters
        -----------
        chat_id: Union[str, int]
            ID of the chat to send the response to
        response: Union[str, dict, dff.connectors.messenger.generics.Response, TelegramResponse]
            Response data. Can be passed as a :py:class:`~str`, a :py:class:`~dict`,
            or a :py:class:`~dff.connectors.messenger.generics.Response`.
            which will then be used to instantiate a :py:class:`~TelegramResponse` object.
            A :py:class:`~TelegramResponse` can also be passed directly.
            Note, that the dict should implement the :py:class:`~TelegramResponse` schema.


        """
        if isinstance(response, TelegramResponse):
            ready_response = response
        elif isinstance(response, str):
            ready_response = TelegramResponse(text=response)
        elif isinstance(response, dict) or isinstance(response, dff.connectors.messenger.generics.Response):
            ready_response = TelegramResponse.parse_obj(response)
        else:
            raise TypeError(
                """
                Type of the response argument should be one of the following: 
                str, dict, TelegramResponse, or dff.connectors.messenger.generics.Response
                """
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
                chat_id=chat_id, latitude=ready_response.location.latitude, longitude=ready_response.location.longitude
            )

        if ready_response.attachments:
            opened_media = [open_io(item) for item in ready_response.attachments.files]
            self.send_media_group(chat_id=chat_id, media=opened_media)
            for item in opened_media:
                close_io(item)

        self.send_message(
            chat_id=chat_id, text=ready_response.text, reply_markup=ready_response.ui and ready_response.ui.keyboard
        )


class ConditionNamespace:
    """
    This class includes methods that produce dff.core.engine conditions based on pytelegrambotapi updates.

    It is included to the :py:class:`~df_telegram_connector.connector.TelegramConnector` as :py:attr:`cnd` attribute.
    This helps us avoid overriding the original methods.

    To set a condition in your script, stick to the signature of the original :py:class:`~telebot.TeleBot` methods.
    E. g. the result of

    .. code-block:: python

        bot.cnd.message_handler(func=lambda msg: True)

    in your :py:class:`~dff.core.engine.core.Script` will always be `True`, unless the new update is not a message.

    """

    def __init__(self, bot: TelegramConnector):
        self.bot = bot

    def handler(
        self, target_type: type, commands=None, regexp=None, func=None, content_types=None, chat_types=None, **kwargs
    ):
        """
        Creates a dff.core.engine condition, triggered by update type {target_type}.
        The signature is equal with the :py:class:`~telebot.Telebot` method of the same name.
        """

        update_handler = self.bot._build_handler_dict(
            None,
            False,
            commands=commands,
            regexp=regexp,
            func=func,
            content_types=content_types,
            chat_types=chat_types,
            **kwargs
        )

        def condition(ctx: Context, actor: Actor, *args, **kwargs):
            update = ctx.framework_states.get("TELEGRAM_CONNECTOR", {}).get("data")
            if not update or not isinstance(update, target_type):
                return False
            test_result = self.bot._test_message_handler(update_handler, update)
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
