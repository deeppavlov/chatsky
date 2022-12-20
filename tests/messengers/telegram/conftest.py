import os
import pytest
import asyncio
import importlib
from pathlib import Path
from telethon import TelegramClient

module_11 = importlib.import_module("examples.messengers.telegram.11_no_pipeline")
bot, actor = module_11.bot, module_11.actor
module_9 = importlib.import_module("examples.messengers.telegram.9_polling_setup")
pipeline = module_9.pipeline


@pytest.fixture(scope="session")
def env_var_presence():
    token = os.getenv("TG_BOT_TOKEN")
    api_id = os.getenv("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")
    if not all([token, api_id, api_hash]):
        raise ValueError("Env vars missing.")
    yield token, api_id, api_hash


@pytest.fixture(scope="session")
def pipeline_instance():
    yield pipeline


@pytest.fixture(scope="session")
def actor_instance():
    yield actor


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
    yield bot


@pytest.fixture(scope="session")
def user_id():
    yield "5889282756"


@pytest.fixture(scope="module")
def event_loop():
    yield asyncio.get_event_loop()


@pytest.fixture(scope="module")
def tg_client(session_file, env_var_presence, event_loop):
    _, _, _ = env_var_presence
    with TelegramClient(
        str(session_file), int(os.getenv("TG_API_ID")), os.getenv("TG_API_HASH"), loop=event_loop
    ) as client:
        yield client
    client: TelegramClient
    client.loop.close()


@pytest.fixture(scope="module")
async def bot_id(tg_client):
    user = await tg_client.get_entity("https://t.me/test_dff_bot")
    yield user


def pytest_sessionfinish(session, exitstatus):
    asyncio.get_event_loop().close()
