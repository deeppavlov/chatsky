import importlib
import logging

import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing import check_happy_path

logger = logging.Logger(__name__)

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "example_module_name",
    [
        "1_basics",
        "2_conditions",
        "3_responses",
        "4_transitions",
        "5_global_transitions",
        "6_context_serialization",
        "7_pre_response_processing",
        "8_misc",
        "9_pre_transitions_processing",
    ],
)
def test_examples(example_module_name: str):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    check_happy_path(example_module.pipeline, example_module.happy_path)
