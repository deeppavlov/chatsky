import os
import time
import importlib
import random
import asyncio
from argparse import Namespace
from urllib import parse
import pytest

try:
    from aiochclient import ChClient
    from httpx import AsyncClient
    import omegaconf  # noqa: F401
    import tqdm  # noqa: F401
    from dff.stats.__main__ import main
    from dff.stats.utils import get_superset_session, drop_superset_assets
    from dff.stats.cli import DEFAULT_SUPERSET_URL
except ImportError:
    pytest.skip(reason="`OmegaConf` dependency missing.", allow_module_level=True)

from tests.stats.chart_data import CHART_DATA, filter_data
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


def charts_data_test(session, headers, base_url=DEFAULT_SUPERSET_URL):
    charts_url = parse.urljoin(DEFAULT_SUPERSET_URL, "/api/v1/chart")

    charts_result = session.get(charts_url, headers=headers)
    charts_json = charts_result.json()

    for _id in sorted(charts_json["ids"]):
        time.sleep(0.5)
        print(str(_id))
        data_result = session.get(
            parse.urljoin(DEFAULT_SUPERSET_URL, f"api/v1/chart/{str(_id)}/data/"), headers=headers
        )
        print(data_result.reason)
        print(data_result.text)
        data_result.raise_for_status()
        data_result_json = data_result.json()
        assert data_result_json["result"][-1]["status"] == "success"
        assert data_result_json["result"][-1]["stacktrace"] is None
        data = data_result_json["result"][-1]["data"]
        filtered_data = filter_data(data)
        assert filtered_data == filter_data(CHART_DATA[_id])
    session.close()


@pytest.mark.skipif(not SUPERSET_ACTIVE, reason="Superset server not active")
@pytest.mark.skipif(not CLICKHOUSE_AVAILABLE, reason="Clickhouse unavailable.")
@pytest.mark.skipif(not COLLECTOR_AVAILABLE, reason="OTLP collector unavailable.")
@pytest.mark.skipif(
    not all([CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DB]), reason="Clickhouse credentials missing"
)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ["example_module_name", "args"],
    [
        (
            "3_sample_data_provider",
            Namespace(
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
            ),
        ),
    ],
)
@pytest.mark.docker
async def test_charts(example_module_name, args, otlp_log_exp_provider, otlp_trace_exp_provider):
    args.__dict__.update(
        {
            "db.password": os.environ["CLICKHOUSE_PASSWORD"],
            "username": os.environ["SUPERSET_USERNAME"],
            "password": os.environ["SUPERSET_PASSWORD"],
            "db.user": os.environ["CLICKHOUSE_USER"],
        }
    )
    session, headers = get_superset_session(args, DEFAULT_SUPERSET_URL)
    module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{example_module_name}")
    _, tracer_provider = otlp_trace_exp_provider
    _, logger_provider = otlp_log_exp_provider
    http_client = AsyncClient()
    table = "otel_logs"
    ch_client = ChClient(http_client, user=CLICKHOUSE_USER, password=CLICKHOUSE_PASSWORD, database=CLICKHOUSE_DB)

    await ch_client.execute(f"TRUNCATE {table}")
    module.dff_instrumentor.uninstrument()
    module.dff_instrumentor.instrument(logger_provider=logger_provider, tracer_provider=tracer_provider)
    await module.main(40)
    await asyncio.sleep(1)

    args.__dict__.update(
        {
            "db.password": os.environ["CLICKHOUSE_PASSWORD"],
            "username": os.environ["SUPERSET_USERNAME"],
            "password": os.environ["SUPERSET_PASSWORD"],
            "db.user": os.environ["CLICKHOUSE_USER"],
        }
    )
    session, headers = get_superset_session(args)
    main(args)
    charts_data_test(session, headers)
    drop_superset_assets(session, headers, DEFAULT_SUPERSET_URL)
