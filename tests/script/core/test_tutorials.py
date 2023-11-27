import importlib
import logging

import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.pipeline import Pipeline
from dff.utils.testing import check_happy_path

logger = logging.Logger(__name__)

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "tutorial_module_name",
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
def test_tutorials(tutorial_module_name: str):
    tutorial_module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    check_happy_path(tutorial_module.pipeline, tutorial_module.happy_path)
    async_pipeline = Pipeline.from_script(
        tutorial_module.toy_script,
        start_label=("root", "start"),
        fallback_label=("root", "fallback") if tutorial_module_name != "6_context_serialization" else None,
        parallelize_processing=True,
    )
    check_happy_path(async_pipeline, tutorial_module.happy_path)
