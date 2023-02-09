"""
Interface
------------
This module implements various interfaces for :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger`
that can be used to interact with the Telegram API.
"""
import asyncio
from typing import Any, Optional, List, Tuple, Callable, cast

from telebot import types, logger

from dff.script import Context
from dff.messengers.common import PollingMessengerInterface, PipelineRunnerFunction, CallbackMessengerInterface
from .messenger import TelegramMessenger
from .message import TelegramMessage, Message, CallbackQuery

try:
    from flask import Flask, request, abort

    flask_imported = True
except ImportError:
    flask_imported = False
    Flask = Any
    request, abort = None, None


def extract_telegram_request_and_id(messenger: TelegramMessenger, update: types.Update) -> Tuple[Message, int]:
    """
    Utility function that extracts parameters from a telegram update.
    Changes the messenger state, setting the last update id.

    Returned message has the following fields:

    - | `update_id` -- this field stores `update.update_id`,
    - | `update` -- this field stores the first non-empty field of `update`,
    - | `update_type` -- this field stores the name of the first non-empty field of `update`,
    - | `text` -- this field stores `update.message.text`,
    - | `commands` -- this field stores a list of one object (a CallbackQuery instance
        with `data=update.callback_query.data`), or None if `data` is None.

    :param messenger: Messenger instance.
    :param update: Update to process.
    """
    if update.update_id > messenger.last_update_id:
        messenger.last_update_id = update.update_id

    message = TelegramMessage(update_id=update.update_id)
    ctx_id = None

    for field in vars(update):
        if field != "update_id":
            inner_update = getattr(update, field)
            if inner_update is not None:
                if message.update is not None:
                    raise RuntimeError(f"Two update fields. First: {message.update_type}; second: {field}")
                message.update_type = field
                message.update = inner_update
                if field == "message":
                    inner_update = cast(types.Message, inner_update)
                    message.text = inner_update.text

                if field == "callback_query":
                    inner_update = cast(types.CallbackQuery, inner_update)
                    data = inner_update.data
                    if data is not None:
                        message.commands = [CallbackQuery(data=data)]

                dict_update = vars(message.update)
                # if 'chat' is not available, fall back to 'from_user', then to 'user'
                user = dict_update.get("chat", dict_update.get("from_user", dict_update.get("user")))
                ctx_id = getattr(user, "id", None)
    if message.update is None:
        raise RuntimeError(f"No update fields found: {update}")

    return message, ctx_id


class PollingTelegramInterface(PollingMessengerInterface):
    """
    Asynchronous Telegram interface that retrieves updates by polling.
    Multi-threaded polling is currently not supported, but will be implemented in the future.

    :param messenger: :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger` instance.
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
        messenger: TelegramMessenger,
        interval: int = 2,
        allowed_updates: Optional[List[str]] = None,
        timeout: int = 20,
        long_polling_timeout: int = 20,
    ):
        self.messenger = messenger
        self.interval = interval
        self.allowed_updates = allowed_updates
        self.timeout = timeout
        self.long_polling_timeout = long_polling_timeout
        self.last_processed_update = -1
        self.stop_polling = asyncio.Event()

    def _request(self) -> List[Tuple[Message, int]]:
        updates = self.messenger.get_updates(
            offset=(self.messenger.last_update_id + 1),
            allowed_updates=self.allowed_updates,
            timeout=self.timeout,
            long_polling_timeout=self.long_polling_timeout,
        )
        update_list = [extract_telegram_request_and_id(self.messenger, update) for update in updates]
        return update_list

    def _respond(self, response: List[Context]):
        for resp in response:
            self.messenger.send_response(resp.id, resp.last_response)
            update_id = getattr(resp.last_request, "update_id", None)
            if update_id is not None:
                if update_id > self.last_processed_update:
                    self.last_processed_update = update_id

    def _on_exception(self, e: Exception):
        logger.error(e)
        self.stop_polling.set()

    async def connect(self, callback: PipelineRunnerFunction, loop: Optional[Callable] = None, *args, **kwargs):
        self.stop_polling.clear()

        try:
            await asyncio.sleep(0)
            await super().connect(
                callback, loop=loop or (lambda: not self.stop_polling.is_set()), timeout=self.interval
            )
        finally:
            self.messenger.get_updates(
                offset=self.last_processed_update + 1,
                allowed_updates=self.allowed_updates,
                timeout=1,
                long_polling_timeout=1,
            )  # forget processed updates

    def stop(self):
        self.stop_polling.set()


class CallbackTelegramInterface(CallbackMessengerInterface):  # pragma: no cover
    """
    Asynchronous Telegram interface that retrieves updates via webhook.
    Any Flask server can be passed to set up a webhook on a separate endpoint.

    :param messenger: :py:class:`~dff.messengers.telegram.messenger.TelegramMessenger` instance.
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
    :param full_uri:
        Full public IP of your webhook that is accessible by https.
        Defaults to `"https://{host}:{port}{endpoint}"`.
    """

    def __init__(
        self,
        messenger: TelegramMessenger,
        app: Optional[Flask] = None,
        host: str = "localhost",
        port: int = 8443,
        endpoint: str = "/telegram-webhook",
        full_uri: Optional[str] = None,
    ):
        if not flask_imported:
            raise ModuleNotFoundError("Flask is not installed. Install it with `pip install flask`.")

        self.messenger = messenger
        self.app = app if app else Flask(__name__)
        self.host = host
        self.port = port
        self.endpoint = endpoint
        self.full_uri = full_uri if full_uri is not None else "".join([f"https://{host}:{port}", endpoint])

        async def endpoint():
            if not request.headers.get("content-type") == "application/json":
                abort(403)

            json_string = request.get_data().decode("utf-8")
            update = types.Update.de_json(json_string)
            return self.on_request(*extract_telegram_request_and_id(self.messenger, update))

        self.app.route(self.endpoint, methods=["POST"])(endpoint)

    async def connect(self, callback: PipelineRunnerFunction):
        await super().connect(callback)

        self.messenger.remove_webhook()
        self.messenger.set_webhook(self.full_uri)

        self.app.run(host=self.host, port=self.port)
