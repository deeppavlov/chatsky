import uuid

from dff.script import Context, Message
import pytest


@pytest.fixture(scope="function")
def testing_context():
    yield Context(
        misc={"some_key": "some_value", "other_key": "other_value"},
        framework_states={"key_for_dict_value": dict()},
        requests={0: Message(text="message text")},
    )


@pytest.fixture(scope="function")
def testing_file(tmpdir_factory):
    filename = tmpdir_factory.mktemp("data").join("file.db")
    string_file = str(filename)
    yield string_file


@pytest.fixture(scope="function")
def context_id():
    ctx_id = str(uuid.uuid4())
    yield ctx_id
