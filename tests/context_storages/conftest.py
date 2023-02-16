import uuid
import asyncio

import nest_asyncio
from dff.script import Context
import pytest

loop = asyncio.get_event_loop_policy().new_event_loop()
nest_asyncio.apply(loop)


@pytest.fixture(scope="function")
def testing_context():
    yield Context(id=112668)


@pytest.fixture(scope="function")
def testing_file(tmpdir_factory):
    filename = tmpdir_factory.mktemp("data").join("file.db")
    string_file = str(filename)
    yield string_file


@pytest.fixture(scope="function")
def context_id():
    ctx_id = str(uuid.uuid4())
    yield ctx_id
