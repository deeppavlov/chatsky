import os
import time
from multiprocessing import Process

from dff.utils.testing.common import run_interactive_mode, is_interactive_mode, set_framework_state
from dff.script import Context
from tests.pipeline.test_messenger_interface import pipeline


def test_set_update():
    ctx = Context()
    new_ctx = set_framework_state(ctx, "update", 1)
    assert new_ctx.framework_states["update"] == 1


def test_is_interactive():
    os.environ["DISABLE_INTERACTIVE_MODE"] = "1"
    assert is_interactive_mode() == False


def test_interactive_mode():
    process = Process(target=run_interactive_mode, args=(pipeline, ), daemon=True)
    process.start()
    time.sleep(1)
    process.kill()
    while process.is_alive():
        time.sleep(0.1)
