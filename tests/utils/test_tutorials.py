import importlib

import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing import check_happy_path

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "tutorial_module_name",
    ["1_cache", "2_lru_cache"],
)
def test_tutorials(tutorial_module_name: str):
    tutorial_module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    check_happy_path(tutorial_module.pipeline, tutorial_module.happy_path)
