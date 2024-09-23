from typing import Iterator

import pytest

from chatsky.core import Context, Message
from chatsky.core.context import FrameworkData


@pytest.fixture(scope="function")
def testing_context() -> Iterator[Context]:
    yield Context(
        requests={0: Message(text="message text")},
        misc={"some_key": "some_value", "other_key": "other_value"},
        framework_data=FrameworkData(key_for_dict_value=dict()),
    )


@pytest.fixture(scope="function")
def testing_file(tmpdir_factory) -> Iterator[str]:
    yield str(tmpdir_factory.mktemp("data").join("file.db"))
