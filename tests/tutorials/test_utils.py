import os
import re

import pytest
from dff.script import Message
from dff.utils.testing.common import check_happy_path, is_interactive_mode
from tests.pipeline.test_messenger_interface import pipeline


def test_unhappy_path():
    with pytest.raises(Exception) as e:
        check_happy_path(pipeline, ((Message(text="Hi"), Message(text="false_response")),))
    assert e
    msg = str(e)
    assert msg
    assert re.search(r"pipeline.+", msg)


def test_is_interactive():
    os.environ["DISABLE_INTERACTIVE_MODE"] = "1"
    assert not is_interactive_mode()
