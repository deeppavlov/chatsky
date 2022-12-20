"""
This script ensures that example scripts can successfully compile and are ready to run
"""
import importlib

import pytest

from tests import test_utils
from dff.utils.testing.toy_script import HAPPY_PATH
from dff.utils.testing.common import check_happy_path

dot_path_to_addon = test_utils.get_path_from_tests_to_current_dir(__file__, separator=".")


def test_unhappy_path(pipeline_instance):
    with pytest.raises(Exception) as e:
        check_happy_path(pipeline_instance, (("Hi", "false_response"),))
    assert e


@pytest.mark.parametrize(
    "example_module_name",
    [
        "1_basic",
        "9_polling_setup",
        "10_webhook_setup"
    ],
)
def test_examples(example_module_name: str):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    check_happy_path(example_module.pipeline, HAPPY_PATH)
