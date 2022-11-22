import importlib

import pytest

import tests.utils as utils
from dff.utils.testing.common import check_happy_path

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "example_module_name",
    ["1_cache", "2_lru_cache"],
)
def test_examples(example_module_name: str):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    check_happy_path(example_module.pipeline, example_module.happy_path)
