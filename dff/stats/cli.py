"""
Command Line Interface
----------------------
This modules defines commands that can be called via the command line interface.

"""
import tempfile
import shutil
import sys
import argparse
import json
import os
import logging
from pathlib import Path
from typing import Optional
from zipfile import ZipFile, ZIP_DEFLATED

try:
    import requests
    from omegaconf import OmegaConf
except ImportError:
    raise ImportError("Some packages are not found. Run `pip install dff[stats]`")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DFF_DIR = Path(__file__).absolute().parent.parent
"""
Root directory of the local `dff` installation.
"""
DASHBOARD_DIR = str(DFF_DIR / "config" / "superset_dashboard")
"""
Local path to superset dashboard files to import.
"""

CLICKHOUSE_TYPES_MAP = {
    "FLOAT": "Nullable(Float64)",
    "STRING": "Nullable(String)",
    "LONGINTEGER": "Nullable(Int64)",
    "INTEGER": "Nullable(Int64)",
    "DATETIME": "Nullable(DateTime(9))",
    "HSTORE": "Map(String, String)",
    "ARRAY(DATETIME)": "Array(DateTime(9))",
    "ARRAY(STRING)": "Array(String)",
    "ARRAY(HSTORE)": "Array(Map(String, String))",
}
"""
Mapping of standard sql column types to Clickhouse native types.
"""
CLICKHOUSE_STATEMENT_SUBSTITUTES = dict(
    logs_table="${db.table}",
    traces_table="otel_traces",
    lag="neighbor(label, -1)",
    context_id_attr="LogAttributes['context_id']",
    request_id_attr="LogAttributes['request_id']",
    label_field="JSON_VALUE(Body, '$.label')",
    flow_field="JSON_VALUE(Body, '$.flow')",
    node_field="JSON_VALUE(Body, '$.node')",
)
"""
Syntax sybstitutes for Clickhouse statements.
"""
POSTGRES_STATEMENT_SUBSTITUTES = dict(
    logs_table="${db.table}",
    traces_table="otel_traces",
    lag="LAG(label,1) OVER (ORDER BY context_id, request_id)",
    context_id_attr="LogAttributes -> 'context_id'",
    request_id_attr="LogAttributes -> 'request_id'",
    label_field="Body -> 'label'",
    flow_field="Body -> 'flow'",
    node_field="Body -> 'node'",
)
"""
Syntax substitutes for PostgreSQL statements.
"""

DFF_NODE_STATS_STATEMENT = """
WITH main as (\nSELECT DISTINCT {logs_table}.{context_id_attr} as context_id,\n
{logs_table}.{request_id_attr} as request_id, \n{logs_table}.Timestamp as start_time,\n
{traces_table}.SpanName as data_key,\n{logs_table}.Body as data,\n
{label_field} as label,\n{flow_field} as flow_label,\n
{node_field} as node_label,\n{logs_table}.TraceId as trace_id,\n
{traces_table}.TraceId\nFROM {logs_table}, {traces_table} \n
WHERE {logs_table}.TraceId = {traces_table}.TraceId and {traces_table}.SpanName = 'get_current_label' \n
ORDER BY context_id, request_id\n) SELECT context_id,\nrequest_id,\nstart_time,\n
data_key,\ndata,\nlabel,\n{lag} as prev_label,\nflow_label,\n
node_label\nFROM main\nWHERE label != ''
"""
DFF_ACYCLIC_NODES_STATEMENT = """
WITH main AS (\nSELECT DISTINCT {logs_table}.{context_id_attr} as context_id,\n
{logs_table}.{request_id_attr} as request_id, \n{logs_table}.Timestamp as timestamp,\n
{label_field} as label\nFROM {logs_table}\n
INNER JOIN \n  (\n  WITH helper AS \n    (\n
SELECT DISTINCT {logs_table}.{context_id_attr} as context_id,\n
{logs_table}.{request_id_attr} as request_id,\n
{label_field} as label\n    FROM {logs_table}\n    )\n
SELECT context_id FROM helper\n  GROUP BY context_id\n  HAVING COUNT(context_id) = COUNT(DISTINCT label)\n
) as plain_ctx\nON plain_ctx.context_id = context_id\n
ORDER by context_id, request_id\n)\nSELECT * FROM main
"""
DFF_FINAL_NODES_STATEMENT = """
WITH main AS\n(\nSELECT {context_id_attr} AS context_id,\nmax({request_id_attr}) AS max_history\n
FROM {logs_table}\nGROUP BY context_id\n)\nSELECT DISTINCT {logs_table}.{context_id_attr} AS context_id,\n
{logs_table}.{request_id_attr} AS request_id,\n{logs_table}.Timestamp AS start_time,\n
{label_field} AS label,\n{flow_field} AS flow_label,\n
{node_field} AS node_label\n FROM {logs_table} \n
INNER JOIN main\nON context_id  = main.context_id \nAND request_id = main.max_history\n
INNER JOIN {traces_table}\nON {logs_table}.TraceId = {traces_table}.TraceId\n
WHERE {traces_table}.SpanName = 'get_current_label'
"""

SQL_STATEMENT_MAPPING = {
    "dff_acyclic_nodes.yaml": DFF_ACYCLIC_NODES_STATEMENT,
    "dff_node_stats.yaml": DFF_NODE_STATS_STATEMENT,
    "dff_final_nodes.yaml": DFF_FINAL_NODES_STATEMENT,
}
"""
Select statements for dashboard configuration with names and types represented as placeholders.
The placeholder system makes queries database agnostic, required values are set during the import phase.
"""


def add_to_zip(zip_file: ZipFile, path: str, zippath: str):
    """
    Recursively add files from a folder to a zip-archive. Recreates the standard
    library function of the same name.

    :param zip_file: File descriptor for source zip file.
    :param path: Path to target file or directory.
    :param zippath: Path to output zip file.
    """
    if os.path.isfile(path):
        zip_file.write(path, zippath, ZIP_DEFLATED)
    elif os.path.isdir(path):
        if zippath:
            zip_file.write(path, zippath)
        for nm in sorted(os.listdir(path)):
            add_to_zip(zip_file, os.path.join(path, nm), os.path.join(zippath, nm))


def import_dashboard(
    parsed_args: Optional[argparse.Namespace] = None,
):
    """
    Import an Apache Superset dashboard to a local instance with specified arguments.
    Before using the command, make sure you have your Superset instance
    up and running: `ghcr.io/deeppavlov/superset_df_dashboard:latest`.

    :param parsed_args: Command line arguments produced by `argparse`.
    """
    zip_file = parsed_args.infile
    zip_filename = os.path.basename(zip_file)
    username = parsed_args.username
    password = parsed_args.password
    db_password = getattr(parsed_args, "db.password")

    BASE_URL = "http://localhost:8088"
    HEALTHCHECK_URL = f"{BASE_URL}/healthcheck"
    LOGIN_URL = f"{BASE_URL}/api/v1/security/login"
    IMPORT_DASHBOARD_URL = f"{BASE_URL}/api/v1/dashboard/import/"
    CSRF_URL = f"{BASE_URL}/api/v1/security/csrf_token/"
    session = requests.Session()

    # do healthcheck
    response = session.get(HEALTHCHECK_URL, timeout=10)
    response.raise_for_status()

    # get access token
    access_request = session.post(
        LOGIN_URL,
        headers={"Content-Type": "application/json", "Accept": "*/*"},
        data=json.dumps({"username": username, "password": password, "refresh": True, "provider": "db"}),
    )
    access_request.raise_for_status()
    access_token = access_request.json()["access_token"]

    # get csrf_token
    csrf_request = session.get(CSRF_URL, headers={"Authorization": f"Bearer {access_token}"})
    csrf_request.raise_for_status()
    csrf_token = csrf_request.json()["result"]

    # upload files
    with open(zip_file, "rb") as f:
        response = session.request(
            "POST",
            IMPORT_DASHBOARD_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "X-CSRFToken": csrf_token,
            },
            data={
                "passwords": '{"databases/dff_database.yaml":"' + db_password + '"}',
                "overwrite": "true",
            },
            files=[("formData", (zip_filename, f, "application/zip"))],
            timeout=10,
        )
        response.raise_for_status()
        logger.info(f"Upload finished with status {response.status_code}.")


def make_zip_config(parsed_args: argparse.Namespace):
    """
    Make a zip-archived Apache Superset dashboard config, using specified arguments.

    :param parsed_args: Command line arguments produced by `argparse`.
    """
    outfile_name = parsed_args.outfile

    if hasattr(parsed_args, "file") and parsed_args.file is not None:  # parse yaml input
        cli_conf = OmegaConf.load(parsed_args.file)
    else:
        sys.argv = [__file__] + [f"{key}={value}" for key, value in parsed_args.__dict__.items()]
        cli_conf = OmegaConf.from_cli()

    if OmegaConf.select(cli_conf, "db.type") == "clickhousedb+connect":
        params = CLICKHOUSE_STATEMENT_SUBSTITUTES
    else:
        params = POSTGRES_STATEMENT_SUBSTITUTES

    conf = SQL_STATEMENT_MAPPING.copy()
    for key in conf.keys():
        conf[key] = {}
        conf[key]["sql"] = SQL_STATEMENT_MAPPING[key].format(**params)

    resolve_conf = OmegaConf.create(
        {
            "database": {
                "sqlalchemy_uri": "${db.type}://${db.user}:XXXXXXXXXX@${db.host}:${db.port}/${db.name}",
            },
            **conf,
        }
    )

    user_config = OmegaConf.merge(cli_conf, resolve_conf)
    OmegaConf.resolve(user_config)

    with tempfile.TemporaryDirectory() as temp_config_dir:
        nested_temp_dir = os.path.join(temp_config_dir, "superset_dashboard")
        logger.info(f"Copying config files to temporary directory: {nested_temp_dir}.")

        shutil.copytree(DASHBOARD_DIR, nested_temp_dir)
        database_dir = Path(os.path.join(nested_temp_dir, "databases"))
        dataset_dir = Path(os.path.join(nested_temp_dir, "datasets/dff_database"))

        logger.info("Overriding the initial configuration.")
        # overwrite sqlalchemy uri
        for filepath in database_dir.iterdir():
            file_config = OmegaConf.load(filepath)
            new_file_config = OmegaConf.merge(file_config, OmegaConf.select(user_config, "database"))
            OmegaConf.save(new_file_config, filepath)

        # overwrite sql expressions and column types
        for filepath in dataset_dir.iterdir():
            file_config = OmegaConf.load(filepath)
            new_file_config = OmegaConf.merge(file_config, getattr(user_config, filepath.name))
            if OmegaConf.select(cli_conf, "db.type") == "clickhousedb+connect":
                for col in OmegaConf.select(new_file_config, "columns"):
                    col.type = CLICKHOUSE_TYPES_MAP.get(col.type, col.type)
            OmegaConf.save(new_file_config, filepath)

        logger.info(f"Saving the archive to {outfile_name}.")

        zip_args = {}
        if sys.version >= "3.8":
            zip_args["strict_timestamps"] = False

        with ZipFile(outfile_name, "w", **zip_args) as zf:
            zippath = os.path.basename(nested_temp_dir)
            if not zippath:
                zippath = os.path.basename(os.path.dirname(nested_temp_dir))
            if zippath in ("", os.curdir, os.pardir):
                zippath = ""
            add_to_zip(zf, nested_temp_dir, zippath)
