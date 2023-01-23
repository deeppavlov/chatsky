import os
import pytest
import asyncio
import importlib
from pathlib import Path
from typing import List
from contextlib import asynccontextmanager
import logging

from telethon import TelegramClient
from telethon.types import User
from telethon.custom import Message as TlMessage

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.pipeline.pipeline.pipeline import Pipeline
from dff.script.core.message import Message, Attachments, Attachment, Button
from dff.messengers.telegram.interface import PollingTelegramInterface
from dff.messengers.telegram.message import TelegramMessage, TelegramUI

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


module_11 = importlib.import_module(f"examples.{dot_path_to_addon}.{'9_no_pipeline'}")
_bot, _actor = module_11.bot, module_11.actor
module_9 = importlib.import_module(f"examples.{dot_path_to_addon}.{'7_polling_setup'}")
_pipeline = module_9.pipeline


@pytest.fixture(scope="session")
def env_var_presence():
    env_variables = {"TG_BOT_TOKEN": None, "TG_API_ID": None, "TG_API_HASH": None}

    for arg in env_variables:
        env_variables[arg] = os.getenv(arg)

        if env_variables[arg] is None:
            raise RuntimeError(f"`{arg}` is not set")

    yield env_variables


@pytest.fixture(scope="session")
def pipeline_instance():
    yield _pipeline


@pytest.fixture(scope="session")
def actor_instance():
    yield _actor


@pytest.fixture(scope="session")
def document(tmpdir_factory):
    filename: Path = tmpdir_factory.mktemp("data").join("file.txt")
    with filename.open("w") as f:
        f.write("test")
    yield filename


@pytest.fixture(scope="session")
def session_file(tmpdir_factory):
    yield "anon"


@pytest.fixture(scope="session")
def basic_bot():
    yield _bot


@pytest.fixture(scope="session")
def event_loop():
    yield asyncio.get_event_loop()


@pytest.fixture(scope="session")
def tg_client(session_file, env_var_presence, event_loop):
    _ = env_var_presence
    client = TelegramClient(
        str(session_file), int(os.getenv("TG_API_ID")), os.getenv("TG_API_HASH"), loop=event_loop
    )
    with client:
        yield client
    client.loop.close()


class Helper:
    """Defines functions for testing."""
    def __init__(self, client: TelegramClient, pipeline: Pipeline, bot: User):
        self.client = client
        """Telegram client (not bot). Needed to verify bot replies."""
        self.pipeline = pipeline
        self.bot = bot
        """Bot user (to know to whom to send messages from client)."""

    def send_message(self, message: Message):
        """Send a message from client to bot."""
        if message.commands is not None:  # Maybe use it to click inline buttons?
            raise RuntimeError("`commands` field is not used in Telegram. Use `text` instead.")
        if message.attachments is None or len(message.attachments.files) == 0:
            return self.client.send_message(self.bot, message.text)
        else:
            if len(message.attachments.files) == 1:
                files = message.attachments.files[0].source
            else:
                files = [file.source for file in message.attachments.files]
            return self.client.send_file(self.bot, files, caption=message.text)

    @staticmethod
    def parse_responses(responses: List[TlMessage], tmp_dir) -> Message:
        """
        Convert a list of bot responses into a single message.
        This function accepts a list because messages with multiple attachments are split.
        """
        msg = TelegramMessage()
        for response in responses:
            if response.text is not None:
                msg.text = response.text
            if response.file is not None:
                file = tmp_dir / str(response.file.media.id) + response.file.ext
                response.download_media(file=file)
                if msg.attachments is None:
                    msg.attachments = Attachments()
                msg.attachments.files.append(Attachment(source=file, title=response.file.title))
            if response.buttons is not None:
                raise NotImplementedError()
                # msg.ui = TelegramUI(buttons=[
                #
                # ])
        return msg

    @asynccontextmanager
    async def run_bot(self):
        """A context manager that start a bot"""
        self.pipeline.messenger_interface.timeout = 2
        self.pipeline.messenger_interface.long_polling_timeout = 2
        task = asyncio.create_task(self.pipeline.messenger_interface.connect(self.pipeline._run_pipeline))
        logging.info("Bot created")
        yield
        self.pipeline.messenger_interface.stop()
        await task

    async def send_and_check(self, message: Message, tmp_dir):
        """Send a message from a bot, receive it as client, verify it."""
        messenger_interface = self.pipeline.messenger_interface
        assert isinstance(messenger_interface, PollingTelegramInterface)

        user_message = await self.send_message(Message(text=f"send_and_check: {repr(message)}"))
        received_user_message = messenger_interface._request()
        if len(received_user_message) != 1:
            raise ValueError(received_user_message)
        else:
            chat_id = received_user_message[0][1]
        messenger_interface.messenger.send_response(chat_id, message)

        await asyncio.sleep(2)
        bot_messages = [
            x async for x in self.client.iter_messages(
                self.bot, min_id=user_message.id, from_user=self.bot
            )
        ]
        bot_messages.reverse()
        result = self.parse_responses(bot_messages, tmp_dir)
        assert result == message

    async def check_happy_path(self, happy_path, tmp_dir):
        async with self.run_bot():
            for request, response in happy_path:
                logging.info("Sending request")
                user_message = await self.send_message(request)
                logging.info("Request sent")
                await asyncio.sleep(3)
                logging.info("Extracting responses")
                bot_messages = [x async for x in self.client.iter_messages(
                    self.bot, min_id=user_message.id, from_user=self.bot
                )
                                ]
                bot_messages.reverse()
                logging.info("Got responses")
                result = self.parse_responses(bot_messages, tmp_dir)
                assert result == response
            self.pipeline.messenger_interface.stop()


@pytest.fixture(scope="session")
def helper():
    return Helper


@pytest.fixture(scope="session")
async def user_id(tg_client):
    user = await tg_client.get_me(input_peer=True)
    yield str(user.user_id)


@pytest.fixture(scope="session")
async def bot_id(tg_client):
    user = await tg_client.get_entity(os.getenv('TG_BOT_USERNAME'))
    yield user


def pytest_sessionfinish(session, exitstatus):
    asyncio.get_event_loop().close()
