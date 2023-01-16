import os
import re

import pytest
from dff.script import Message
from dff.utils.testing.common import check_happy_path, is_interactive_mode, set_framework_state
from dff.script import Context
from tests.pipeline.test_messenger_interface import pipeline


def test_unhappy_path():
    with pytest.raises(Exception) as e:
        check_happy_path(pipeline, ((Message(text="Hi"), Message(text="false_response")),))
    assert e
    msg = str(e)
    assert msg
    assert re.search(r"pipeline.+", msg)


def test_set_update():
    ctx = Context()
    new_ctx = set_framework_state(ctx, "update", 1)
    assert new_ctx.framework_states["update"] == 1


def test_is_interactive():
    os.environ["DISABLE_INTERACTIVE_MODE"] = "1"
    assert is_interactive_mode() == False
