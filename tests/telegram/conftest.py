import pytest

from .examples.no_runner.basic_bot import bot, actor

# for variable in ["BOT_TOKEN"]:
#     if variable not in os.environ:
#         raise AssertionError(f"{variable} variable needs to be set to continue")


@pytest.fixture(scope="session")
def actor_instance():
    yield actor


@pytest.fixture(scope="session")
def basic_bot():
    yield bot
