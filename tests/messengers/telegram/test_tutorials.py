from importlib import import_module
from json import loads
from pathlib import Path

import pytest

from dff.messengers.telegram import telegram_available
from tests.test_utils import get_path_from_tests_to_current_dir

if telegram_available:
    from tests.messengers.telegram.utils import cast_dict_to_happy_step, MockApplication

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")
happy_paths_file = Path(__file__).parent / "test_happy_paths.json"


@pytest.mark.skipif(not telegram_available, reason="Telegram dependencies missing")
@pytest.mark.parametrize(
    "tutorial_module_name",
    ["1_basic", "2_attachments", "3_advanced"],
)
def test_tutorials_memory(tutorial_module_name: str, monkeypatch):
    monkeypatch.setenv("TG_BOT_TOKEN", "token")
    happy_path_data = loads(happy_paths_file.read_text())[tutorial_module_name]
    happy_path_steps = cast_dict_to_happy_step(happy_path_data)
    module = import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    module.interface.application = MockApplication.create(module.interface, happy_path_steps)
    module.pipeline.run()
