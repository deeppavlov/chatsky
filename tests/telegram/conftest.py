import os
import pytest
from pathlib import Path
from telethon import TelegramClient

from examples.telegram.no_pipeline.basic_bot import bot, actor
from examples.telegram.basics.polling import pipeline
from dff.utils.testing.common import check_env_var


@pytest.fixture(scope="session")
def env_var_presence():
    yield check_env_var("BOT_TOKEN"), check_env_var("TG_API_ID"), check_env_var("TG_API_HASH")


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
    filename = tmpdir_factory.mktemp("session").join("session.session")
    yield Path(filename).absolute()


@pytest.fixture(scope="session")
def basic_bot():
    yield bot


@pytest.fixture(scope="session")
def user_id():
    yield "5947503209"


@pytest.fixture(scope="module")
def tg_client(session_file, env_var_presence):
    _, _, _ = env_var_presence
    with TelegramClient(str(session_file), os.getenv("TG_API_ID"), os.getenv("TG_API_HASH")) as client:
        yield client
