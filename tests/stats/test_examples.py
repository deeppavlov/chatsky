import importlib
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.common import check_happy_path
from dff.utils.testing.toy_script import HAPPY_PATH

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__)


@pytest.mark.parametrize(
    "example_module_name",
    [
        "1_services_basic",
        "2_services_advanced",
        "3_service_groups_basic",
        "4_service_groups_advanced",
        "5_global_services_basic",
        "6_global_services_advanced",
    ],
)
def test_examples(example_module_name: str, testing_file: str):
    module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    try:
        pipeline = module.pipeline
        stats = module.StatsStorage.from_uri(f"csv://{testing_file}", "")
        stats.add_extractor_pool(module.extractor_pool)
        check_happy_path(pipeline, HAPPY_PATH)
        with open(testing_file, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()
            assert len(lines) > 1
    except Exception as exc:
        raise Exception(f"model_name=examples.{dot_path_to_addon}.{example_module_name}") from exc
