import csv
import importlib
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.common import check_happy_path
from dff.utils.testing.toy_script import HAPPY_PATH

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__)


@pytest.mark.parametrize(
    ["example_module_name", "num_rows"],
    [
        ("1_services_basic", 10),
        ("2_services_advanced", 20),
        ("3_service_groups", 10),
        ("4_global_services", 10),
    ],
)
def test_examples(example_module_name: str, num_rows: int, testing_file: str):
    module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{example_module_name}")
    try:
        pipeline = module.pipeline
        stats = module.StatsStorage.from_uri(f"csv://{testing_file}", "")
        module.extractor_pool.add_subscriber(stats)
        if "default_extractor_pool" in vars(module):
            module.default_extractor_pool.add_subscriber(stats)
        check_happy_path(pipeline, HAPPY_PATH)
        with open(testing_file, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            rows = [row for row in reader]
            assert len(rows) == num_rows

    except Exception as exc:
        raise Exception(f"model_name=tutorials.{dot_path_to_addon}.{example_module_name}") from exc
