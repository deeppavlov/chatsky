"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""
import asyncio
from typing import Any, Optional, List, Tuple, Callable

from telebot import types, logger

from dff.script import Context
from dff.messengers.common import PollingMessengerInterface, PipelineRunnerFunction, CallbackMessengerInterface
from .messenger import TelegramMessenger
from .message import TelegramMessage, Message

try:
    from flask import Flask, request, abort

    flask_imported = True
except ImportError:
    flask_imported = False
    Flask = Any
    request, abort = None, None


def extract_telegram_request_and_id(
    update: types.Update, messenger: Optional[TelegramMessenger] = None
) -> Tuple[TelegramMessage, int]:  # pragma: no cover
    """
    Utility function that extracts parameters from a telegram update.
    Changes the messenger state, setting the last update id.

    Returned message has the following fields:

    - | `update_id` -- this field stores `update.update_id`,
    - | `update` -- this field stores the first non-empty field of `update`,
    - | `update_type` -- this field stores the name of the first non-empty field of `update`,
    - | `text` -- this field stores `update.message.text`,
    - | `callback_query` -- this field stores `update.callback_query.data`.

    Also return context id which is `chat`, `from_user` or `user` of the update.

    :param update: Update to process.
    :param messenger:
        Messenger instance. If passed updates `last_update_id`.
        Defaults to None.
    """
    if messenger is not None:
        if update.update_id > messenger.last_update_id:
            messenger.last_update_id = update.update_id

    message = TelegramMessage(update_id=update.update_id)
    ctx_id = None

    for update_field, update_value in vars(update).items():
        if update_field != "update_id" and update_value is not None:
            if message.update is not None:
                raise RuntimeError(f"Two update fields. First: {message.update_type}; second: {update_field}")
            message.update_type = update_field
            message.update = update_value
            if isinstance(update_value, types.Message):
                message.text = update_value.text

            if isinstance(update_value, types.CallbackQuery):
                data = update_value.data
                if data is not None:
                    message.callback_query = data

            dict_update = vars(update_value)
            # if 'chat' is not available, fall back to 'from_user', then to 'user'
            user = dict_update.get("chat", dict_update.get("from_user", dict_update.get("user")))
            ctx_id = getattr(user, "id", None)
    if message.update is None:
        raise RuntimeError(f"No update fields found: {update}")

    return message, ctx_id


class PollingTelegramInterface(PollingMessengerInterface):  # pragma: no cover
    """
    Telegram interface that retrieves updates by polling.
    Multi-threaded polling is currently not supported.

    :param token: Bot token
    :param messenger:
        :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger` instance.
        If not `None` will be used instead of creating messenger from token.
        Token value does not matter in that case.
        Defaults to None.
    :param interval:
        Polling interval. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`__.
        Defaults to 2.
    :param allowed_updates:
        Processed updates. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`__.
        Defaults to None.
    :param timeout:
        General timeout. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`__.
        Defaults to 20.
    :param long_polling_timeout:
        Polling timeout. See `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`__.
        Defaults to 20.
    """

    def __init__(
        self,
        token: str,
        interval: int = 2,
        allowed_updates: Optional[List[str]] = None,
        timeout: int = 20,
        long_polling_timeout: int = 20,
        messenger: Optional[TelegramMessenger] = None,
    ):
        self.messenger = messenger if messenger is not None else TelegramMessenger(token)
        self.interval = interval
        self.allowed_updates = allowed_updates
        self.timeout = timeout
        self.long_polling_timeout = long_polling_timeout
        self._last_processed_update = -1
        self._stop_polling = asyncio.Event()

    def _request(self) -> List[Tuple[Message, int]]:
        updates = self.messenger.get_updates(
            offset=(self.messenger.last_update_id + 1),
            allowed_updates=self.allowed_updates,
            timeout=self.timeout,
            long_polling_timeout=self.long_polling_timeout,
        )
        update_list = [extract_telegram_request_and_id(update, self.messenger) for update in updates]
        return update_list

    def _respond(self, response: List[Context]):
        for resp in response:
            self.messenger.send_response(resp.id, resp.last_response)
            update_id = getattr(resp.last_request, "update_id", None)
            if update_id is not None:
                if update_id > self._last_processed_update:
                    self._last_processed_update = update_id

    def _on_exception(self, e: Exception):
        logger.error(e)
        self._stop_polling.set()

    def forget_processed_updates(self):
        """
        Forget updates already processed by the pipeline.
        """
        self.messenger.get_updates(
            offset=self._last_processed_update + 1,
            allowed_updates=self.allowed_updates,
            timeout=1,
            long_polling_timeout=1,
        )

    async def connect(self, callback: PipelineRunnerFunction, loop: Optional[Callable] = None, *args, **kwargs):
        self._stop_polling.clear()

        try:
            await super().connect(
                callback, loop=loop or (lambda: not self._stop_polling.is_set()), timeout=self.interval
            )
        finally:
            self.forget_processed_updates()

    def stop(self):
        """Stop polling."""
        self._stop_polling.set()


class CallbackTelegramInterface(CallbackMessengerInterface):  # pragma: no cover
    """
    Asynchronous Telegram interface that retrieves updates via webhook.
    Any Flask server can be passed to set up a webhook on a separate endpoint.

    :param token: Bot token
    :param messenger:
        :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger` instance.
        If not `None` will be used instead of creating messenger from token.
        Token value does not matter in that case.
        Defaults to None.
    :param app:
        Flask instance.
        Defaults to `Flask(__name__)`.
    :param endpoint:
        Webhook endpoint. Should be prefixed with "/".
        Defaults to "/telegram-webhook".
    :param host:
        Host IP.
        Defaults to "localhost".
    :param port:
        Port of the app.
        Defaults to 8443.
    :param debug:
        Run the Flask app in debug mode.
    :param load_dotenv:
        Whether or not the .env file in the project folder
        should be used to set environment variables.
    :param full_uri:
        Full public IP of your webhook that is accessible by https.
        Defaults to `"https://{host}:{port}{endpoint}"`.
    :param wsgi_options:
        Keyword arguments to forward to `Flask.run` method.
        Use these to set `ssl_context` and other WSGI options.
    """

    def __init__(
        self,
        token: str,
        app: Optional[Flask] = None,
        host: str = "localhost",
        port: int = 8443,
        debug: Optional[bool] = None,
        load_dotenv: bool = True,
        endpoint: str = "/telegram-webhook",
        full_uri: Optional[str] = None,
        messenger: Optional[TelegramMessenger] = None,
        **wsgi_options,
    ):
        if not flask_imported:
            raise ModuleNotFoundError("Flask is not installed. Install it with `pip install flask`.")

        self.messenger = messenger if messenger is not None else TelegramMessenger(token)
        self.app = app if app else Flask(__name__)
        self.host = host
        self.port = port
        self.debug = debug
        self.load_dotenv = load_dotenv
        self.wsgi_options = wsgi_options
        self.endpoint = endpoint
        self.full_uri = full_uri if full_uri is not None else "".join([f"https://{host}:{port}", endpoint])

        async def endpoint():
            if not request.headers.get("content-type") == "application/json":
                abort(403)

            json_string = request.get_data().decode("utf-8")
            update = types.Update.de_json(json_string)
            resp = self.on_request(*extract_telegram_request_and_id(update, self.messenger))
            self.messenger.send_response(resp.id, resp.last_response)
            return ""

        self.app.route(self.endpoint, methods=["POST"])(endpoint)

    async def connect(self, callback: PipelineRunnerFunction):
        await super().connect(callback)

        self.messenger.remove_webhook()
        self.messenger.set_webhook(self.full_uri)

        self.app.run(
            host=self.host, port=self.port, load_dotenv=self.load_dotenv, debug=self.debug, **self.wsgi_options
        )
