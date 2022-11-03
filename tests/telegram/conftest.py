import pytest

from examples.telegram._telegram_utils import check_env_bot_tokens
from examples.telegram.no_pipeline.basic_bot import bot, actor


@pytest.fixture(scope="session")
def env_var_presence():
    yield check_env_bot_tokens()


@pytest.fixture(scope="session")
def actor_instance():
    yield actor


@pytest.fixture(scope="session")
def basic_bot():
    yield bot
