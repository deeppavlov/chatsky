from pathlib import Path

from df_engine.core.context import Context
import pytest


@pytest.fixture(scope="function")
def testing_context():
    yield Context(id=112668)


@pytest.fixture(scope="function")
def testing_file(tmpdir_factory):
    filename = tmpdir_factory.mktemp("data").join("file.db")
    Path(filename).touch()
    string_file = str(filename)
    yield string_file


@pytest.fixture(scope="function")
def testing_telegram_id():
    yield "123123123"
