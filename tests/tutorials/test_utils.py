import os

import pytest
from chatsky.utils.testing.common import check_happy_path, is_interactive_mode
from tests.pipeline.test_messenger_interface import pipeline


def test_unhappy_path():
    with pytest.raises(AssertionError):
        check_happy_path(pipeline, (("Hi", "false_response"),))


def test_is_interactive():
    os.environ["DISABLE_INTERACTIVE_MODE"] = "1"
    assert not is_interactive_mode()
