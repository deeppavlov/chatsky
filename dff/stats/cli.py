"""
Command Line Interface
----------------------
This modules defines commands that can be called via the command line interface.

"""
from uuid import uuid4
import tempfile
import shutil
import sys
import argparse
import os
import logging
from urllib import parse
from pathlib import Path
from typing import Optional

try:
    from omegaconf import OmegaConf
    from .utils import get_superset_session, drop_superset_assets
except ImportError:
    raise ImportError("Some packages are not found. Run `pip install dff[stats]`")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DFF_DIR = Path(__file__).absolute().parent.parent
"""
Root directory of the local `dff` installation.

:meta hide-value:
"""
DASHBOARD_DIR = str(DFF_DIR / "config" / "superset_dashboard")
"""
Local path to superset dashboard files to import.

:meta hide-value:
"""
DASHBOARD_SLUG = "dff-stats"
"""
This variable stores a slug used for building the http address of the DFF dashboard.
"""
DEFAULT_SUPERSET_URL = parse.urlunsplit(("http", "localhost:8088", "/", "", ""))
"""
Default location of the Superset dashboard.
"""

TYPE_MAPPING_CH = {
    "FLOAT": "Nullable(Float64)",
    "STRING": "Nullable(String)",
    "LONGINTEGER": "Nullable(Int64)",
    "INTEGER": "Nullable(Int64)",
    "DATETIME": "Nullable(DateTime)",
}
"""
Mapping of standard sql column types to Clickhouse native types.

:meta hide-value:
"""

DFF_NODE_STATS_STATEMENT = """
WITH main AS (
    SELECT DISTINCT {table}.LogAttributes['context_id'] as context_id,
    toUInt64OrNull({table}.LogAttributes['request_id']) as request_id,
    toDateTime(otel_traces.Timestamp) as start_time,
    otel_traces.SpanName as data_key,
    {table}.Body as data,
    {lblfield} as label,
    {flowfield} as flow_label,
    {nodefield} as node_label,
    {table}.TraceId as trace_id,
    otel_traces.TraceId\nFROM {table}, otel_traces
    WHERE {table}.TraceId = otel_traces.TraceId and data_key = 'get_current_label'
    ORDER BY context_id, request_id
) SELECT context_id,
    request_id,
    start_time,
    data_key,
    data,
    label,
    {label_lag} as prev_label,
    {flow_lag} as prev_flow,
    flow_label,
    node_label
FROM main
"""
DFF_STATS_STATEMENT = """
WITH main AS (
    SELECT DISTINCT {table}.LogAttributes['context_id'] as context_id,
    toUInt64OrNull({table}.LogAttributes['request_id']) as request_id,
    toDateTime(otel_traces.Timestamp) as start_time,
    otel_traces.SpanName as data_key,
    {table}.Body as data,
    {lblfield} as label,
    {flowfield} as flow_label,
    {nodefield} as node_label,
    {table}.TraceId as trace_id,
    otel_traces.TraceId\nFROM {table}, otel_traces
    WHERE {table}.TraceId = otel_traces.TraceId
    ORDER BY data_key, context_id, request_id
) SELECT context_id,
    request_id,
    start_time,
    data_key,
    data,
    label,
    {label_lag} as prev_label,
    {flow_lag} as prev_flow,
    flow_label,
    node_label
FROM main
"""
DFF_FINAL_NODES_STATEMENT = """
WITH main AS (
    SELECT LogAttributes['context_id'] AS context_id,
    max(toUInt64OrNull(LogAttributes['request_id'])) AS max_history
    FROM {table}\nGROUP BY context_id
)
SELECT DISTINCT LogAttributes['context_id'] AS context_id,
toUInt64OrNull({table}.LogAttributes['request_id']) AS request_id,
toDateTime(otel_traces.Timestamp) AS start_time,
{lblfield} AS label,
{flowfield} AS flow_label,
{nodefield} AS node_label
FROM {table}
INNER JOIN main
ON context_id  = main.context_id
AND request_id = main.max_history
INNER JOIN otel_traces
ON {table}.TraceId = otel_traces.TraceId
WHERE otel_traces.SpanName = 'get_current_label'
"""

SQL_STATEMENT_MAPPING = {
    "dff_stats.yaml": DFF_STATS_STATEMENT,
    "dff_node_stats.yaml": DFF_NODE_STATS_STATEMENT,
    "dff_final_nodes.yaml": DFF_FINAL_NODES_STATEMENT,
}
"""
Select statements for dashboard configuration with names and types represented as placeholders.
The placeholder system makes queries database agnostic, required values are set during the import phase.

:meta hide-value:
"""


def import_dashboard(parsed_args: Optional[argparse.Namespace] = None, zip_file: Optional[str] = None):
    """
    Import an Apache Superset dashboard to a local instance with specified arguments.
    Before using the command, make sure you have your Superset instance
    up and running: `ghcr.io/deeppavlov/superset_df_dashboard:latest`.
    The import will override existing dashboard configurations if present.

    :param parsed_args: Command line arguments produced by `argparse`.
    :param zip_file: Zip archived dashboard config.
    """
    host = parsed_args.host if hasattr(parsed_args, "host") else "localhost"
    port = parsed_args.port if hasattr(parsed_args, "port") else "8088"
    superset_url = parse.urlunsplit(("http", f"{host}:{port}", "/", "", ""))
    zip_filename = os.path.basename(zip_file)
    db_password = getattr(parsed_args, "db.password")

    session, headers = get_superset_session(parsed_args, superset_url)
    drop_superset_assets(session, headers, superset_url)
    import_dashboard_url = parse.urljoin(superset_url, "/api/v1/dashboard/import/")
    # upload files
    with open(zip_file, "rb") as f:
        response = session.request(
            "POST",
            import_dashboard_url,
            headers=headers,
            data={
                "passwords": '{"databases/dff_database.yaml":"' + db_password + '"}',
                "overwrite": "true",
            },
            files=[("formData", (zip_filename, f, "application/zip"))],
        )
        response.raise_for_status()
        logger.info(f"Upload finished with status {response.status_code}.")


def make_zip_config(parsed_args: argparse.Namespace) -> Path:
    """
    Make a zip-archived Apache Superset dashboard config, using specified arguments.

    :param parsed_args: Command line arguments produced by `argparse`.
    """
    if hasattr(parsed_args, "outfile") and parsed_args.outfile:
        outfile_name = parsed_args.outfile
    else:
        outfile_name = f"config_{str(uuid4())}.zip"

    file_conf = OmegaConf.load(parsed_args.file)
    sys.argv = [__file__] + [f"{key}={value}" for key, value in parsed_args.__dict__.items() if value]
    cmd_conf = OmegaConf.from_cli()
    cli_conf = OmegaConf.merge(file_conf, cmd_conf)

    if OmegaConf.select(cli_conf, "db.driver") == "clickhousedb+connect":
        params = dict(
            table="${db.table}",
            label_lag="lagInFrame(label) OVER "
            "(PARTITION BY context_id ORDER BY request_id ASC "
            "ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)",
            flow_lag="lagInFrame(flow_label) OVER "
            "(PARTITION BY context_id ORDER BY request_id ASC "
            "ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)",
            texttype="String",
            lblfield="JSON_VALUE(${db.table}.Body, '$.label')",
            flowfield="JSON_VALUE(${db.table}.Body, '$.flow')",
            nodefield="JSON_VALUE(${db.table}.Body, '$.node')",
        )
    else:
        raise ValueError("The only supported database driver is 'clickhousedb+connect'.")

    conf = SQL_STATEMENT_MAPPING.copy()
    for key in conf.keys():
        conf[key] = {}
        conf[key]["sql"] = SQL_STATEMENT_MAPPING[key].format(**params)

    resolve_conf = OmegaConf.create(
        {
            "database": {
                "sqlalchemy_uri": "${db.driver}://${db.user}:XXXXXXXXXX@${db.host}:${db.port}/${db.name}",
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
            if OmegaConf.select(cli_conf, "db.driver") == "clickhousedb+connect":
                for col in OmegaConf.select(new_file_config, "columns"):
                    col.type = TYPE_MAPPING_CH.get(col.type, col.type)
            OmegaConf.save(new_file_config, filepath)

        if ".zip" not in outfile_name:
            raise ValueError(f"Outfile name missing .zip extension: {outfile_name}.")
        logger.info(f"Saving the archive to {outfile_name}.")
        shutil.make_archive(outfile_name[: outfile_name.rindex(".zip")], format="zip", root_dir=temp_config_dir)

    return Path(outfile_name)
