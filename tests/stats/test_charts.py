import os
import random
import json
import asyncio
from argparse import Namespace
from urllib import parse
import pytest

try:
    import omegaconf  # noqa: F401
    import tqdm  # noqa: F401
    from dff.stats.__main__ import main
    from dff.stats.utils import get_superset_session, drop_superset_assets
    from dff.stats.cli import DEFAULT_SUPERSET_URL
    from utils.stats.utils import cleanup_clickhouse
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


def transitions_data_test(session, headers, base_url=DEFAULT_SUPERSET_URL):
    charts_url = parse.urljoin(DEFAULT_SUPERSET_URL, "/api/v1/chart")

    result = session.get(charts_url, headers=headers)
    result.raise_for_status()
    result_json = result.json()

    target_chart_id = [item for item in result_json["result"] if item["slice_name"] == "Transition counts"][0]["id"]
    target_url = parse.urljoin(DEFAULT_SUPERSET_URL, f"api/v1/chart/{target_chart_id}/data/")
    data_result = session.get(target_url, headers=headers)
    data_result.raise_for_status()
    data_result_json = data_result.json()
    data = data_result_json["result"][0]["data"]
    assert (len(data)) > 0
    assert "COUNT_DISTINCT(context_id)" in data[0]
    assert data[0]["COUNT_DISTINCT(context_id)"] == 10
    session.close()


def numbered_data_test(session, headers, base_url=DEFAULT_SUPERSET_URL):
    charts_url = parse.urljoin(DEFAULT_SUPERSET_URL, "/api/v1/chart")

    result = session.get(charts_url, headers=headers)
    result.raise_for_status()
    result_json = result.json()

    target_chart_id = [item for item in result_json["result"] if item["slice_name"] == "Table"][0]["id"]
    target_url = parse.urljoin(DEFAULT_SUPERSET_URL, f"api/v1/chart/{target_chart_id}/data/")
    data_result = session.get(target_url, headers=headers)
    data_result.raise_for_status()
    data_result_json = data_result.json()
    grouped_dict = dict()
    for item in data_result_json["result"][0]["data"]:
        if item["context_id"] not in grouped_dict:
            grouped_dict[item["context_id"]] = [item]
        else:
            grouped_dict[item["context_id"]].append(item)
    unique_flows = list(map(lambda x: set(map(lambda y: json.loads(y["data"])["flow"], x)), grouped_dict.values()))
    assert all(map(lambda x: len(x) == 1, unique_flows))
    session.close()


config_namespace = Namespace(
    **{
        "outfile": "1.zip",
        "db.driver": "clickhousedb+connect",
        "db.host": "clickhouse",
        "db.port": "8123",
        "db.name": "test",
        "db.table": "otel_logs",
        "host": "localhost",
        "port": "8088",
        "file": f"tutorials/{dot_path_to_addon}/example_config.yaml",
    }
)


@pytest.mark.skipif(not SUPERSET_ACTIVE, reason="Superset server not active")
@pytest.mark.skipif(not CLICKHOUSE_AVAILABLE, reason="Clickhouse unavailable.")
@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="OTLP collector unavailable.")
@pytest.mark.skipif(
    not all([CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DB]), reason="Clickhouse credentials missing"
)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["args", "pipeline", "func"],
    [
        (config_namespace, numbered_test_pipeline, numbered_data_test),
        (config_namespace, transition_test_pipeline, transitions_data_test),
    ],
)
@pytest.mark.docker
async def test_charts(args, pipeline, func, otlp_log_exp_provider, otlp_trace_exp_provider):
    args.__dict__.update(
        {
            "db.password": os.environ["CLICKHOUSE_PASSWORD"],
            "username": os.environ["SUPERSET_USERNAME"],
            "password": os.environ["SUPERSET_PASSWORD"],
            "db.user": os.environ["CLICKHOUSE_USER"],
        }
    )
    session, headers = get_superset_session(args, DEFAULT_SUPERSET_URL)
    _, tracer_provider = otlp_trace_exp_provider
    _, logger_provider = otlp_log_exp_provider

    await cleanup_clickhouse("otel_logs", CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DB)
    await loop(pipeline=pipeline)  # run with a test-specific pipeline
    await asyncio.sleep(5)

    drop_superset_assets(session, headers, DEFAULT_SUPERSET_URL)
    main(args)
    func(session, headers)  # run with a test-specific function with equal signature
