import importlib
import pytest
from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.common import (
    check_happy_path
)

# uncomment the following line, if you want to run your examples during the test suite or import from them
dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "tutorial_module_name",
    [
        "1_basic_example",
        "2_form_example",
        "3_handlers_example",
    ],
)
def test_examples(tutorial_module_name, root):
    root.children.clear()
    module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    pipeline = getattr(module, "pipeline")
    happy_path = getattr(module, "HAPPY_PATH")
    check_happy_path(pipeline, happy_path)
