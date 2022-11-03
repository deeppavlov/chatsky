"""
This script ensures that example scripts can successfully compile and are ready to run
"""
import importlib

import pytest

from tests import utils

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")
example_utils = importlib.import_module(f"examples.{dot_path_to_addon}._telegram_utils")


@pytest.mark.parametrize(
    "example_module_name",
    [
        "basics.flask",
        "basics.polling",
    ],
)
def test_examples(example_module_name: str):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    example_utils.auto_run_pipeline(pipeline=example_module.pipeline)
