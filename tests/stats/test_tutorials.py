import importlib
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.common import check_happy_path
from dff.utils.testing.toy_script import HAPPY_PATH

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__)


@pytest.mark.parametrize(
    ["example_module_name"],
    [
        ("1_services_basic",),
        ("2_services_advanced",),
        ("3_service_groups",),
        ("4_global_services",),
    ],
)
def test_examples(example_module_name: str):
    module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{example_module_name}")
    try:
        pipeline = module.pipeline
        check_happy_path(pipeline, HAPPY_PATH)

    except Exception as exc:
        raise Exception(f"model_name=tutorials.{dot_path_to_addon}.{example_module_name}") from exc
