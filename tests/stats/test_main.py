import os
import pytest
from urllib import parse
from zipfile import ZipFile
from argparse import Namespace

try:
    import omegaconf  # noqa: F401
    from dff.stats.__main__ import main
    from dff.stats.cli import DEFAULT_SUPERSET_URL, DASHBOARD_SLUG
    from dff.stats.utils import get_superset_session
except ImportError:
    pytest.skip(reason="`OmegaConf` dependency missing.", allow_module_level=True)

from tests.db_list import SUPERSET_ACTIVE
from tests.test_utils import get_path_from_tests_to_current_dir

path_to_addon = get_path_from_tests_to_current_dir(__file__)


def dashboard_display_test(args: Namespace, base_url: str):
    dashboard_url = parse.urljoin(base_url, f"/api/v1/dashboard/{DASHBOARD_SLUG}")
    charts_url = parse.urljoin(base_url, "/api/v1/chart")
    datasets_url = parse.urljoin(base_url, "/api/v1/dataset")

    session, headers = get_superset_session(args, base_url)
    dashboard_res = session.get(dashboard_url, headers=headers)
    assert dashboard_res.status_code == 200
    dashboard_json = dashboard_res.json()
    assert dashboard_json["result"]["charts"] == [
        "Flow visit ratio monitor",
        "Node Visits",
        "Node counts",
        "Node visit ratio monitor",
        "Node visits [cloud]",
        "Node visits [ratio]",
        "Node visits [sunburst]",
        "Service load [max dialogue length]",
        "Service load [users]",
        "Table",
        "Terminal labels",
        "Transition counts",
        "Transition layout",
        "Transition ratio [chord]",
    ]
    assert dashboard_json["result"]["url"] == "/superset/dashboard/dff-stats/"
    assert dashboard_json["result"]["dashboard_title"] == "DFF Stats"
    datasets_result = session.get(datasets_url, headers=headers)
    datasets_json = datasets_result.json()
    assert datasets_json["count"] == 2
    assert datasets_json["ids"] == [1, 2]
    assert [item["id"] for item in datasets_json["result"]] == [1, 2]
    assert sorted([item["table_name"] for item in datasets_json["result"]]) == [
        "dff_final_nodes",
        "dff_node_stats",
    ]
    charts_result = session.get(charts_url, headers=headers)
    charts_json = charts_result.json()
    assert charts_json["count"] == 14
    assert sorted(charts_json["ids"]) == list(range(1, 15))
    session.close()


@pytest.mark.skipif(not SUPERSET_ACTIVE, reason="Superset server not active")
@pytest.mark.parametrize(
    ["args"],
    [
        (
            Namespace(
                **{
                    "outfile": "1.zip",
                    "db.type": "postgresql",
                    "db.user": "root",
                    "db.host": "localhost",
                    "db.port": "5000",
                    "db.name": "test",
                    "db.table": "dff_stats",
                    "username": os.getenv("SUPERSET_USERNAME"),
                    "password": os.getenv("SUPERSET_PASSWORD"),
                    "host": "localhost",
                    "port": "8088",
                    "db.password": "qwerty",
                    "file": f"tutorials/{path_to_addon}/example_config.yaml",
                }
            ),
        ),
        (
            Namespace(
                **{
                    "outfile": "2.zip",
                    "db.type": "mysql+mysqldb",
                    "db.user": "root",
                    "db.host": "localhost",
                    "db.port": "5000",
                    "db.name": "test",
                    "db.table": "dff_stats",
                    "username": os.getenv("SUPERSET_USERNAME"),
                    "password": os.getenv("SUPERSET_PASSWORD"),
                    "host": "localhost",
                    "port": "8088",
                    "db.password": "qwerty",
                    "file": f"tutorials/{path_to_addon}/example_config.yaml",
                }
            ),
        ),
        (
            Namespace(
                **{
                    "outfile": "3.zip",
                    "db.type": "clickhousedb+connect",
                    "db.user": "root",
                    "db.host": "localhost",
                    "db.port": "5000",
                    "db.name": "test",
                    "db.table": "dff_stats",
                    "username": os.getenv("SUPERSET_USERNAME"),
                    "password": os.getenv("SUPERSET_PASSWORD"),
                    "host": "localhost",
                    "port": "8088",
                    "db.password": "qwerty",
                    "file": f"tutorials/{path_to_addon}/example_config.yaml",
                }
            ),
        ),
    ],
)
def test_main(testing_cfg_dir, args):
    args.outfile = testing_cfg_dir + args.outfile
    main(args)
    dashboard_display_test(args, base_url=DEFAULT_SUPERSET_URL)
    assert os.path.exists(args.outfile)
    assert os.path.isfile(args.outfile)
    assert os.path.getsize(args.outfile) > 2200
    with ZipFile(args.outfile) as file:
        file.extractall(testing_cfg_dir)
    database = omegaconf.OmegaConf.load(os.path.join(testing_cfg_dir, "superset_dashboard/databases/dff_database.yaml"))
    sqlalchemy_uri = omegaconf.OmegaConf.select(database, "sqlalchemy_uri")
    arg_vars = vars(args)
    _type, user, host, port, name = (
        arg_vars["db.type"],
        arg_vars["db.user"],
        arg_vars["db.host"],
        arg_vars["db.port"],
        arg_vars["db.name"],
    )
    assert sqlalchemy_uri == f"{_type}://{user}:XXXXXXXXXX@{host}:{port}/{name}"


@pytest.mark.parametrize(["cmd"], [("dff.stats -h",), ("dff.stats --help",)])
def test_help(cmd):
    res = os.system(cmd)
    assert res == 0
