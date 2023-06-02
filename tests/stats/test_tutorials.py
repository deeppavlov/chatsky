import importlib
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.common import check_happy_path
from dff.utils.testing.toy_script import HAPPY_PATH

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__)


@pytest.mark.parametrize(
    ["example_module_name", "expected_logs"],
    [
        ("1_services_basic", 10),
        ("2_services_advanced", 30),
        ("3_service_groups", 15),
        ("4_global_services", 10),
    ],
)
def test_examples(example_module_name: str, expected_logs, tracer_exporter_and_provider, log_exporter_and_provider):
    module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{example_module_name}")
    _, tracer_provider = tracer_exporter_and_provider
    log_exporter, logger_provider = log_exporter_and_provider
    try:
        pipeline = module.pipeline
        module.dff_instrumentor.uninstrument()
        module.dff_instrumentor.instrument(logger_provider=logger_provider, tracer_provider=tracer_provider)
        check_happy_path(pipeline, HAPPY_PATH)
        tracer_provider.force_flush()
        logger_provider.force_flush()
        assert len(log_exporter.get_finished_logs()) == expected_logs

    except Exception as exc:
        raise Exception(f"model_name=tutorials.{dot_path_to_addon}.{example_module_name}") from exc
