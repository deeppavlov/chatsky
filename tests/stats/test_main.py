import os
import pytest
from urllib import parse
from zipfile import ZipFile
from argparse import Namespace

try:
    import omegaconf  # noqa: F401
    from dff.stats.__main__ import main
    from dff.stats.cli import DEFAULT_SUPERSET_URL, DASHBOARD_SLUG
    from dff.stats.utils import get_superset_session, drop_superset_assets
except ImportError:
    pytest.skip(reason="`OmegaConf` dependency missing.", allow_module_level=True)

from tests.context_storages.test_dbs import ping_localhost
from tests.test_utils import get_path_from_tests_to_current_dir

SUPERSET_ACTIVE = ping_localhost(8088)
path_to_addon = get_path_from_tests_to_current_dir(__file__)


def dashboard_display_test(args: Namespace, session, headers, base_url: str):
    dashboard_url = parse.urljoin(base_url, f"/api/v1/dashboard/{DASHBOARD_SLUG}")
    charts_url = parse.urljoin(base_url, "/api/v1/chart")
    datasets_url = parse.urljoin(base_url, "/api/v1/dataset")
    database_conn_url = parse.urljoin(base_url, "/api/v1/database/test_connection")
    db_driver, db_user, db_password, db_host, db_port, db_name = (
        getattr(args, "db.driver"),
        getattr(args, "db.user"),
        getattr(args, "db.password"),
        getattr(args, "db.host"),
        getattr(args, "db.port"),
        getattr(args, "db.name"),
    )
    sqla_url = f"{db_driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    database_data = {
        "configuration_method": "sqlalchemy_form",
        "database_name": "dff_database",
        "driver": "string",
        "engine": None,
        "extra": "",
        "impersonate_user": False,
        "masked_encrypted_extra": "",
        "parameters": {},
        "server_cert": None,
        "sqlalchemy_uri": sqla_url,
        "ssh_tunnel": None,
    }

    database_res = session.post(database_conn_url, json=database_data, headers=headers)
    assert database_res.status_code == 200
    dashboard_res = session.get(dashboard_url, headers=headers)
    assert dashboard_res.status_code == 200
    dashboard_json = dashboard_res.json()
    print(dashboard_json["result"]["charts"])
    assert sorted(dashboard_json["result"]["charts"]) == [
        "Current topic [time series bar chart]",
        "Current topic slot [bar chart]",
        "Flow visit ratio monitor",
        "Node Visits",
        "Node counts",
        "Node visit ratio monitor",
        "Node visits [ratio]",
        "Node visits [sunburst]",
        "Rating slot [line chart]",
        "Requests",
        "Responses",
        "Service load [users]",
        "Table",
        "Terminal labels",
        "Transition counts",
        "Transition layout",
        "Transition ratio [chord]",
    ]
    assert dashboard_json["result"]["url"] == "/superset/dashboard/dff-stats/"
    assert dashboard_json["result"]["dashboard_title"] == "DFF statistics dashboard"
    datasets_result = session.get(datasets_url, headers=headers)
    datasets_json = datasets_result.json()
    assert datasets_json["count"] == 3
    assert datasets_json["ids"] == [1, 2, 3]
    assert [item["id"] for item in datasets_json["result"]] == [1, 2, 3]
    assert sorted([item["table_name"] for item in datasets_json["result"]]) == [
        "dff_final_nodes",
        "dff_node_stats",
        "dff_stats",
    ]
    charts_result = session.get(charts_url, headers=headers)
    charts_json = charts_result.json()
    assert charts_json["count"] == 17
    assert sorted(charts_json["ids"]) == list(range(1, 18))
    session.close()


@pytest.mark.skipif(not SUPERSET_ACTIVE, reason="Superset server not active")
@pytest.mark.parametrize(
    ["args"],
    [
        (
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
                    "file": f"tutorials/{path_to_addon}/example_config.yaml",
                }
            ),
        ),
    ],
)
@pytest.mark.docker
def test_main(testing_cfg_dir, args):
    args.__dict__.update(
        {
            "db.password": os.environ["CLICKHOUSE_PASSWORD"],
            "username": os.environ["SUPERSET_USERNAME"],
            "password": os.environ["SUPERSET_PASSWORD"],
            "db.user": os.environ["CLICKHOUSE_USER"],
        }
    )
    args.outfile = testing_cfg_dir + args.outfile
    session, headers = get_superset_session(args, DEFAULT_SUPERSET_URL)
    dashboard_url = parse.urljoin(DEFAULT_SUPERSET_URL, "/api/v1/dashboard/")

    drop_superset_assets(session, headers, DEFAULT_SUPERSET_URL)
    dashboard_result = session.get(dashboard_url, headers=headers)
    dashboard_json = dashboard_result.json()
    assert dashboard_json["count"] == 0

    main(args)
    dashboard_display_test(args, session, headers, base_url=DEFAULT_SUPERSET_URL)
    assert os.path.exists(args.outfile)
    assert os.path.isfile(args.outfile)
    assert os.path.getsize(args.outfile) > 2200
    with ZipFile(args.outfile) as file:
        file.extractall(testing_cfg_dir)
    database = omegaconf.OmegaConf.load(os.path.join(testing_cfg_dir, "superset_dashboard/databases/dff_database.yaml"))
    sqlalchemy_uri = omegaconf.OmegaConf.select(database, "sqlalchemy_uri")
    arg_vars = vars(args)
    driver, user, host, port, name = (
        arg_vars["db.driver"],
        arg_vars["db.user"],
        arg_vars["db.host"],
        arg_vars["db.port"],
        arg_vars["db.name"],
    )
    assert sqlalchemy_uri == f"{driver}://{user}:XXXXXXXXXX@{host}:{port}/{name}"


@pytest.mark.parametrize(["cmd"], [("dff.stats -h",), ("dff.stats --help",)])
def test_help(cmd):
    res = os.system(cmd)
    assert res == 0
