import pytest

from examples.telegram.no_pipeline.basic_bot import bot, actor
from examples.telegram.basics.polling import pipeline
from dff.utils.testing.common import check_env_var


@pytest.fixture(scope="session")
def env_var_presence():
    yield check_env_var("BOT_TOKEN")


@pytest.fixture(scope="session")
def pipeline_instance():
    yield pipeline


@pytest.fixture(scope="session")
def actor_instance():
    yield actor


@pytest.fixture(scope="session")
def basic_bot():
    yield bot


@pytest.fixture(scope="session")
def user_id():
    yield "405094684"
