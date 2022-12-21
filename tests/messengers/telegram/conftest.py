import os
import pytest
import asyncio
import importlib
from pathlib import Path
from telethon import TelegramClient
from tests.test_utils import get_path_from_tests_to_current_dir

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


module_11 = importlib.import_module(f"examples.{dot_path_to_addon}.{'11_no_pipeline'}")
bot, actor = module_11.bot, module_11.actor
module_9 = importlib.import_module(f"examples.{dot_path_to_addon}.{'9_polling_setup'}")
pipeline = module_9.pipeline


@pytest.fixture(scope="session")
def env_var_presence():
    env_variables = {
        "TG_BOT_TOKEN": None,
        "TG_API_ID": None,
        "TG_API_HASH": None
    }

    for arg in env_variables:
        env_variables[arg] = os.getenv(arg)

        if env_variables[arg] is None:
            raise RuntimeError(f"`{arg}` is not set")
    
    yield env_variables


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
    _ = env_var_presence
    with TelegramClient(
        str(session_file), int(os.getenv("TG_API_ID")), os.getenv("TG_API_HASH"), loop=event_loop
    ) as client:
        yield client
    client.loop.close()


@pytest.fixture(scope="module")
async def bot_id(tg_client):
    user = await tg_client.get_entity("https://t.me/test_dff_bot")
    yield user


def pytest_sessionfinish(session, exitstatus):
    asyncio.get_event_loop().close()
