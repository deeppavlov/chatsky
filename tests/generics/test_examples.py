import importlib

import pytest

import tests.utils as utils

dot_path_to_addon = utils.get_dot_path_from_tests_to_current_dir(__file__)
example_utils = importlib.import_module(f"examples.{dot_path_to_addon}._example_utils")


@pytest.mark.parametrize(
    "example_module_name",
    [
        "basics",
        "buttons",
    ],
)
def test_examples(example_module_name: str):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    example_utils.run_test(actor=example_module.actor, testing_dialog=example_module.testing_dialog)
