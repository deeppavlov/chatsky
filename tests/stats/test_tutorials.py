import os
import importlib
import pytest
import asyncio

from tests.test_utils import get_path_from_tests_to_current_dir
from tests.context_storages.test_dbs import ping_localhost
from dff.utils.testing.common import check_happy_path
from dff.utils.testing.toy_script import HAPPY_PATH

try:
    from aiochclient import ChClient
    from httpx import AsyncClient
    from dff import stats  # noqa: F401
except ImportError:
    pytest.skip(allow_module_level=True, reason="There are dependencies missing.")


dot_path_to_addon = get_path_from_tests_to_current_dir(__file__)


COLLECTOR_AVAILABLE = ping_localhost(4317)
CLICKHOUSE_AVAILABLE = ping_localhost(8123)
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB")


@pytest.mark.skipif(not CLICKHOUSE_AVAILABLE, reason="Clickhouse unavailable.")
@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="OTLP collector unavailable.")
@pytest.mark.skipif(
    not all([CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DB]), reason="Clickhouse credentials missing"
)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["tutorial_module_name", "expected_logs"],
    [
        ("1_extractor_functions", 10),
        ("2_pipeline_integration", 35),
    ],
)
@pytest.mark.docker
async def test_tutorials_ch(tutorial_module_name: str, expected_logs, otlp_log_exp_provider, otlp_trace_exp_provider):
    module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    _, tracer_provider = otlp_trace_exp_provider
    _, logger_provider = otlp_log_exp_provider
    http_client = AsyncClient()
    table = "otel_logs"
    ch_client = ChClient(http_client, user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD, database=CLICKHOUSE_DB)

    try:
        await ch_client.execute(f"TRUNCATE {table}")
        pipeline = module.pipeline
        module.dff_instrumentor.uninstrument()
        module.dff_instrumentor.instrument(logger_provider=logger_provider, tracer_provider=tracer_provider)
        check_happy_path(pipeline, HAPPY_PATH)
        await asyncio.sleep(3)
        count = await ch_client.fetchval(f"SELECT COUNT (*) FROM {table}")
        assert count == expected_logs

    except Exception as exc:
        raise Exception(f"model_name=tutorials.{dot_path_to_addon}.{tutorial_module_name}") from exc


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["tutorial_module_name", "expected_logs"],
    [
        ("1_extractor_functions", 10),
        ("2_pipeline_integration", 35),
    ],
)
async def test_tutorials_memory(
    tutorial_module_name: str, expected_logs, tracer_exporter_and_provider, log_exporter_and_provider
):
    module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    _, tracer_provider = tracer_exporter_and_provider
    log_exporter, logger_provider = log_exporter_and_provider
    try:
        pipeline = module.pipeline
        module.dff_instrumentor.uninstrument()
        module.dff_instrumentor.instrument(logger_provider=logger_provider, tracer_provider=tracer_provider)
        check_happy_path(pipeline, HAPPY_PATH)
        tracer_provider.force_flush()
        logger_provider.force_flush()
        await asyncio.sleep(1)
        assert len(log_exporter.get_finished_logs()) == expected_logs

    except Exception as exc:
        raise Exception(f"model_name=tutorials.{dot_path_to_addon}.{tutorial_module_name}") from exc
