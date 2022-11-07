import importlib

import pytest

import tests.utils as utils
from dff.utils.generics import run_example

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "example_module_name",
    [
        "basics",
        "buttons",
    ],
)
def test_examples(example_module_name: str):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    run_example(example_module.logger, actor=example_module.actor, happy_path=example_module.testing_dialog)
