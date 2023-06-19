import os
import asyncio
import importlib
from pathlib import Path

import pytest

from tests.test_utils import get_path_from_tests_to_current_dir

try:
    from dff.utils.testing.telegram import get_bot_user, TelegramClient

    telegram_available = True
except ImportError:
    telegram_available = False

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.fixture(scope="session")
def pipeline_tutorial():
    if not telegram_available:
        pytest.skip("`telegram` not available.")
    yield importlib.import_module(f"tutorials.{dot_path_to_addon}.{'7_polling_setup'}")


@pytest.fixture(scope="session")
def session_file():
    dff_root_dir = Path(__file__).parent.parent.parent.parent
    file = dff_root_dir / "anon.session"

    if not file.exists():
        pytest.skip(f"Session file does not exist at {str(file)}")

    return str(file)


@pytest.fixture(scope="session")
def env_vars():
    env_variables = {"TG_BOT_TOKEN": None, "TG_API_ID": None, "TG_API_HASH": None, "TG_BOT_USERNAME": None}

    for arg in env_variables:
        env_variables[arg] = os.getenv(arg)

        if env_variables[arg] is None:
            pytest.skip(f"`{arg}` is not set", allow_module_level=True)

    yield env_variables


@pytest.fixture(scope="session")
def pipeline_instance(env_vars, pipeline_tutorial):
    yield pipeline_tutorial.pipeline


@pytest.fixture(scope="session")
def document(tmpdir_factory):
    filename: Path = tmpdir_factory.mktemp("data").join("file.txt")
    with filename.open("w") as f:
        f.write("test")
    yield filename


@pytest.fixture(scope="session")
def api_credentials(env_vars):
    yield (int(env_vars["TG_API_ID"]), env_vars["TG_API_HASH"])


@pytest.fixture(scope="session")
def bot_user(api_credentials, env_vars, session_file):
    if not telegram_available:
        pytest.skip("`telegram` not available.")
    client = TelegramClient(session_file, *api_credentials)
    yield asyncio.run(get_bot_user(client, env_vars["TG_BOT_USERNAME"]))


def pytest_sessionfinish(session, exitstatus):
    asyncio.get_event_loop().close()
