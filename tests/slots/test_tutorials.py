import importlib
import pytest
from tests.test_utils import get_path_from_tests_to_current_dir
from chatsky.utils.testing.common import check_happy_path


dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "tutorial_module_name",
    [
        "1_basic_example",
    ],
)
def test_examples(tutorial_module_name):
    module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    pipeline = getattr(module, "pipeline")
    happy_path = getattr(module, "HAPPY_PATH")
    check_happy_path(pipeline, happy_path)
