"""
Telegram tutorial test data
---------------------------

Generate telegram tutorial test data.

.. code:: bash

    python utils/test_data_generators/telegram_tutorial_data.py
"""

from importlib import import_module
import importlib.machinery
from json import loads, dump
from typing import List
from pathlib import Path
import os
from contextlib import contextmanager

from chatsky.script import Message


ROOT = Path(__file__).parent.parent.parent
TG_TUTORIALS = ROOT / "tutorials" / "telegram"
TG_TESTS = ROOT / "tests" / "messengers" / "telegram"
HAPPY_PATH_FILE = TG_TESTS / "test_happy_paths.json"


test_utils = importlib.machinery.SourceFileLoader(fullname="utils", path=str(TG_TESTS / "utils.py")).load_module()

MockApplication = test_utils.MockApplication
cast_dict_to_happy_step = test_utils.cast_dict_to_happy_step


if __name__ == "__main__":
    happy_path_data = loads(HAPPY_PATH_FILE.read_text())

    os.environ["TG_BOT_TOKEN"] = "token"

    for tutorial in ["1_basic", "2_attachments", "3_advanced"]:
        happy_path_update = []

        @contextmanager
        def _check_context_and_trace_patch(self, last_request: Message, last_response: Message, last_trace: List[str]):
            self.bot.latest_trace = list()
            self.latest_ctx = None
            yield
            happy_path_update.append(
                {
                    "received_message": self.latest_ctx.last_request.model_dump(mode="json"),
                    "response_message": self.latest_ctx.last_response.model_dump(mode="json"),
                    "response_functions": self.bot.latest_trace,
                }
            )

        MockApplication._check_context_and_trace = _check_context_and_trace_patch

        happy_path_steps = cast_dict_to_happy_step(happy_path_data[tutorial], update_only=True)
        module = import_module(f"tutorials.messengers.telegram.{tutorial}")
        module.interface.application = MockApplication.create(module.interface, happy_path_steps)
        module.pipeline.run()

        for value, update in zip(happy_path_data[tutorial], happy_path_update):
            value.update(update)

    with open(HAPPY_PATH_FILE, "w", encoding="utf-8") as fp:
        dump(happy_path_data, fp, indent=4)
