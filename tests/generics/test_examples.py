import importlib

import pytest

import tests.utils as utils
from dff.utils.testing import check_happy_path, generics_comparer, default_comparer

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "example_module_name",
    ["1_basics", "2_buttons", "3_media"],
)
def test_examples(example_module_name: str):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    if example_module_name == "1_basics":
        comparer = default_comparer
    else:
        comparer = generics_comparer
    check_happy_path(example_module.pipeline, example_module.happy_path, comparer)
