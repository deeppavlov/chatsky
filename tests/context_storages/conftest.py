from typing import Iterator

from chatsky.core import Context, Message
from chatsky.script.core.context import FrameworkData
from chatsky.utils.context_dict import ContextDict
import pytest


@pytest.fixture(scope="function")
def testing_context() -> Iterator[Context]:
    yield Context(
        misc={"some_key": "some_value", "other_key": "other_value"},
        framework_data=FrameworkData(key_for_dict_value=dict()),
        requests={0: Message(text="message text")},
    )


@pytest.fixture(scope="function")
def testing_file(tmpdir_factory) -> Iterator[str]:
    yield str(tmpdir_factory.mktemp("data").join("file.db"))
