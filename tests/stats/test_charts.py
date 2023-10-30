import os
import time
from argparse import Namespace
from urllib import parse
import pytest
from dff.stats.utils import get_superset_session
from dff.stats.cli import DEFAULT_SUPERSET_URL
from tests.stats.chart_data import CHART_DATA  # noqa: F401
from tests.context_storages.test_dbs import ping_localhost

SUPERSET_ACTIVE = ping_localhost(8088)


@pytest.mark.skipif(not SUPERSET_ACTIVE, reason="Superset server not active")
@pytest.mark.docker
def test_charts():
    charts_url = parse.urljoin(DEFAULT_SUPERSET_URL, "/api/v1/chart")
    args = Namespace(
        **{
            "username": os.environ["SUPERSET_USERNAME"],
            "password": os.environ["SUPERSET_PASSWORD"],
        }
    )
    session, headers = get_superset_session(args)
    charts_result = session.get(charts_url, headers=headers)
    charts_json = charts_result.json()

    for _id in sorted(charts_json["ids"]):
        time.sleep(0.1)
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
        ignored_keys = ["context_id", "__timestamp", "start_time", "data"]
        _ = [{key: value} for item in data for key, value in item.items() if key not in ignored_keys]
        # assert _ == CHART_DATA[_id]
    session.close()
