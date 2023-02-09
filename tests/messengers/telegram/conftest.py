import os
import asyncio
import importlib
from pathlib import Path

import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.telegram import TelegramTesting

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
def basic_bot():
    yield _bot


@pytest.fixture(scope="session")
def test_helper():
    yield TelegramTesting(pipeline=None)


def pytest_sessionfinish(session, exitstatus):
    asyncio.get_event_loop().close()
