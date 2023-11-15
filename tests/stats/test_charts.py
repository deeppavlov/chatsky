import os
import random
import json
import asyncio
from argparse import Namespace
from urllib import parse
import pytest

try:
    from requests import Session
    import omegaconf  # noqa: F401
    import tqdm  # noqa: F401
    from dff.stats.utils import get_superset_session
    from dff.stats.cli import DEFAULT_SUPERSET_URL
    from aiochclient import ChClient
    from httpx import AsyncClient
except ImportError:
    pytest.skip(reason="`OmegaConf` dependency missing.", allow_module_level=True)

from tests.stats.chart_data import numbered_test_pipeline, transition_test_pipeline, loop
from tests.context_storages.test_dbs import ping_localhost
from tests.test_utils import get_path_from_tests_to_current_dir

random.seed(42)
dot_path_to_addon = get_path_from_tests_to_current_dir(__file__)

SUPERSET_ACTIVE = ping_localhost(8088)
COLLECTOR_AVAILABLE = ping_localhost(4317)
CLICKHOUSE_AVAILABLE = ping_localhost(8123)
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB")
SUPERSET_USERNAME = os.getenv("SUPERSET_USERNAME")
SUPERSET_PASSWORD = os.getenv("SUPERSET_PASSWORD")


async def transitions_data_test(session: Session, headers: dict, base_url=DEFAULT_SUPERSET_URL):
    charts_url = parse.urljoin(DEFAULT_SUPERSET_URL, "/api/v1/chart")

    result = session.get(charts_url, headers=headers)
    result.raise_for_status()
    result_json = result.json()

    target_chart_id = [item for item in result_json["result"] if item["slice_name"] == "Transition counts"][0]["id"]
    target_url = parse.urljoin(DEFAULT_SUPERSET_URL, f"api/v1/chart/{target_chart_id}/data/")
    result_status = 404
    attempts = 0
    while result_status != 200 and attempts < 10:
        attempts += 1
        data_result = session.get(target_url, headers=headers)
        result_status = data_result.status_code
        await asyncio.sleep(1)

    data_result_json = data_result.json()
    data = data_result_json["result"][0]["data"]
    assert (len(data)) > 0
    assert "COUNT_DISTINCT(context_id)" in data[0]
    assert data[0]["COUNT_DISTINCT(context_id)"] == 10
    session.close()


async def numbered_data_test(session: Session, headers: dict, base_url=DEFAULT_SUPERSET_URL):
    charts_url = parse.urljoin(DEFAULT_SUPERSET_URL, "/api/v1/chart")

    result = session.get(charts_url, headers=headers)
    result.raise_for_status()
    result_json = result.json()

    target_chart_id = [item for item in result_json["result"] if item["slice_name"] == "Table"][0]["id"]
    target_url = parse.urljoin(DEFAULT_SUPERSET_URL, f"api/v1/chart/{target_chart_id}/data/")
    result_status = 404
    attempts = 0
    while result_status != 200 and attempts < 10:
        attempts += 1
        data_result = session.get(target_url, headers=headers)
        result_status = data_result.status_code
        await asyncio.sleep(2)

    data_result_json = data_result.json()
    grouped_dict = dict()
    data = data_result_json["result"][0]["data"]
    assert len(data) > 0
    for item in data:
        if item["context_id"] not in grouped_dict:
            grouped_dict[item["context_id"]] = [item]
        else:
            grouped_dict[item["context_id"]].append(item)
    unique_flows = list(map(lambda x: set(map(lambda y: json.loads(y["data"])["flow"], x)), grouped_dict.values()))
    assert all(map(lambda x: len(x) == 1, unique_flows))
    session.close()


@pytest.mark.skipif(not SUPERSET_ACTIVE, reason="Superset server not active")
@pytest.mark.skipif(not CLICKHOUSE_AVAILABLE, reason="Clickhouse unavailable.")
@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="OTLP collector unavailable.")
@pytest.mark.skipif(
    not all([CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DB]), reason="Clickhouse credentials missing"
)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["pipeline", "func"],
    [
        (numbered_test_pipeline, numbered_data_test),
        (transition_test_pipeline, transitions_data_test),
    ],
)
@pytest.mark.docker
async def test_charts(pipeline, func, otlp_log_exp_provider, otlp_trace_exp_provider):
    _, tracer_provider = otlp_trace_exp_provider
    _, logger_provider = otlp_log_exp_provider

    table = "otel_logs"
    http_client = AsyncClient()
    ch_client = ChClient(http_client, user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD, database=CLICKHOUSE_DB)
    await ch_client.execute(f"TRUNCATE {table}")
    await loop(pipeline=pipeline)  # run with a test-specific pipeline
    tracer_provider.force_flush()
    logger_provider.force_flush()
    num_records = 0

    attempts = 0
    while num_records < 10 and attempts < 10:
        attempts += 1
        await asyncio.sleep(2)
        num_records = await ch_client.fetchval(f"SELECT COUNT (*) FROM {table}")

    os.system(
        f"dff.stats tutorials/stats/example_config.yaml \
            -U {SUPERSET_USERNAME} \
            -P {SUPERSET_PASSWORD} \
            -dP {CLICKHOUSE_PASSWORD}"
    )
    session, headers = get_superset_session(
        Namespace(**{"username": SUPERSET_USERNAME, "password": SUPERSET_PASSWORD}), DEFAULT_SUPERSET_URL
    )
    await func(session, headers)  # run with a test-specific function with equal signature
