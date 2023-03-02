import sys
import importlib
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.stats_cli import parse_args
from dff.utils.testing.common import check_happy_path
from dff.utils.testing.toy_script import HAPPY_PATH

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__)


@pytest.mark.parametrize("args", [
    [
        '',
        'cfg_from_opts',
        '--db.type=postgresql',
        '--db.user=user',
        '--db.password=password',
        '--db.host=localhost',
        '--db.port=5432',
        '--db.name=db',
        '--db.table=test'
    ],
    ['', 'cfg_from_file', '--db.password=pass', './examples/stats/example_config.yaml'],
    ['', 'cfg_from_uri', '--uri=postgresql://user:password@localhost:5432/db/test']
])
def test_parse_args(args):
    sys.argv = args
    assert parse_args()


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
