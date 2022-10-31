import importlib

import pytest

import tests.utils as utils

dot_path_to_addon = utils.get_dot_path_from_tests_to_current_dir(__file__)
engine_utils = importlib.import_module(f"examples.{dot_path_to_addon}._engine_utils")


@pytest.mark.parametrize(
    "example_module_name",
    [
        "example_1_basics",
        "example_2_conditions",
        "example_3_responses",
        "example_4_transitions",
        "example_5_global_transitions",
        "example_6_context_serialization",
        "example_7_pre_response_processing",
        "example_8_misc",
        "example_9_pre_transitions_processing",
    ],
)
def test_examples(example_module_name: str):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    engine_utils.run_auto_mode(example_module.actor, example_module.testing_dialog, example_module.logger)
