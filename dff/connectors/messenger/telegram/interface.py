"""
Request Provider
*****************
This module contains several variations of the `RequestProvider` class that can be used
to combine :py:class:`~df_telegram_connector.connector.TelegramConnector`
together with the `df_runner` add-on.
"""
from typing import Any, Optional, List, Tuple, Hashable, Callable

from telebot import types, logger

from dff.core.engine.core import Context
from dff.core.pipeline import PollingMessengerInterface, PipelineRunnerFunction, CallbackMessengerInterface
from .connector import DFFTeleBot
from .utils import get_user_id

flask_imported: bool
try:
    from flask import Flask, request, abort

    flask_imported = True
except ImportError:
    flask_imported = False
    Flask = Any
    request, abort = None, None


class TelegramInterfaceMixin:
    bot: DFFTeleBot

    """
    Abstract class for Telegram request providers.
    Subclass it, or use one of the child classes below.

    :param bot: An instance of :py:class:`~df_telegram_connector.connector.TelegramConnector`.
        Note that passing a regular `Telebot` instance will result in an error.
    """

    def __init__(self, bot: DFFTeleBot):
        self.bot = bot

    def _extract_telegram_request_and_id(self, update: types.Update) -> Tuple[Any, Hashable]:
        if update.update_id > self.bot.last_update_id:
            self.bot.last_update_id = update.update_id

        update_fields = vars(update).copy()
        update_fields.pop("update_id")
        inner_update = next(filter(lambda val: val is not None, list(update_fields.values())))

        ctx_id = get_user_id(inner_update)
        return inner_update, ctx_id


class PollingTelegramInterface(PollingMessengerInterface, TelegramInterfaceMixin):
    """
    Class for compatibility with df_runner. Retrieves updates by polling.
    Multi-threaded polling is currently not supported, but will be implemented in the future.

    :param bot: An instance of :py:class:`~df_telegram_connector.connector.TelegramConnector`.
        Note that passing a regular `Telebot` instance will result in an error.
    :param args: The rest of the parameters are equal to those of the `polling` method of a regular `Telebot`.
        See the pytelegrambotapi docs for more info:
        `link <https://github.com/eternnoir/pyTelegramBotAPI#telebot>`_ .
    """

    def __init__(self, bot: DFFTeleBot, interval=3, allowed_updates=None, timeout=20, long_polling_timeout=20):
        TelegramInterfaceMixin.__init__(self, bot)
        self.interval = interval
        self.allowed_updates = allowed_updates
        self.timeout = timeout
        self.long_polling_timeout = long_polling_timeout

    def _request(self) -> List[Tuple[Any, Hashable]]:
        updates = self.bot.get_updates(
            offset=(self.bot.last_update_id + 1),
            allowed_updates=self.allowed_updates,
            timeout=self.timeout,
            long_polling_timeout=self.long_polling_timeout,
        )
        lst = [self._extract_telegram_request_and_id(update) for update in updates]
        return lst

    def _respond(self, response: List[Context]):
        for resp in response:
            self.bot.send_response(resp.id, resp.last_response)

    def _except(self, e: Exception):
        logger.error(e)
        self.bot._TeleBot__stop_polling.set()

    async def connect(self, callback: PipelineRunnerFunction, loop: Optional[Callable] = None, *args, **kwargs):
        self.bot._TeleBot__stop_polling.clear()
        self.bot.get_updates(offset=-1)

        await super().connect(callback, loop=loop or (lambda: not self.bot._TeleBot__stop_polling.wait(self.interval)))


class FlaskTelegramInterface(CallbackMessengerInterface, TelegramInterfaceMixin):
    """
    Class for compatibility with df_runner. Retrieves updates from post json requests.

    :param bot: An instance of :py:class:`~df_telegram_connector.connector.TelegramConnector`.
        Note that passing a regular `Telebot` instance will result in an error.
    :param app: An instance of a `Flask` application. It may have any number of endpoints,
        but the endpoint you pass to this constructor should be reserved.
    :param endpoint: The endpoint to which the webhook is bound. Like any flask endpoint,
        it should always be prefixed with a forward slash ("/").
    :param host: The host IP.
    :param port: The port of the app.
    :param full_uri: Setting up a webhook requires a public IP that is accessible by https. If you are hosting
        your application, this is where you pass the full public URL of your webhook.
    """

    def __init__(
        self,
        bot: DFFTeleBot,
        app: Flask,
        host: str = "localhost",
        port: int = 8443,
        endpoint: str = "/dff-bot",
        full_uri: Optional[str] = None,
    ):
        if not flask_imported:
            raise ModuleNotFoundError("Flask is not installed")

        TelegramInterfaceMixin.__init__(self, bot=bot)
        self.app: Flask = app
        self.host: str = host
        self.port: int = port
        self.endpoint: str = endpoint
        self.full_uri: str = full_uri or "".join([f"https://{host}:{port}", endpoint])

    async def connect(self, callback: PipelineRunnerFunction):
        async def endpoint():
            if not request.headers.get("content-type") == "application/json":
                abort(403)

            json_string = request.get_data().decode("utf-8")
            update = types.Update.de_json(json_string)
            return self.on_request(*self._extract_telegram_request_and_id(update))

        await super().connect(callback)

        self.app.route(self.endpoint, methods=["POST"])(endpoint)
        self.bot.remove_webhook()
        self.bot.set_webhook(self.full_uri)

        self.app.run(host=self.host, port=self.port)
