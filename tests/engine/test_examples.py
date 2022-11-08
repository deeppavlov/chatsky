import importlib
import logging

import pytest

import tests.utils as utils
from dff.utils.testing.common import check_happy_path

logger = logging.Logger(__name__)

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")


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
    check_happy_path(example_module.pipeline, example_module.happy_path)
