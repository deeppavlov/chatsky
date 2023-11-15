import os
import subprocess
from aiochclient import ChClient
from httpx import AsyncClient


async def cleanup_clickhouse(table: str, user: str, password: str, database: str):
    http_client = AsyncClient()
    ch_client = ChClient(http_client, user=user, password=password, database=database)
    await ch_client.execute(f"TRUNCATE {table}")


def restart_pk():
    id_reset_cmd = """sh -c "psql --user={} --password -p {} --db=test -c \'
    ALTER SEQUENCE {}_id_seq RESTART WITH 1;
    ALTER SEQUENCE {}_id_seq RESTART WITH 1;
    ALTER SEQUENCE {}_id_seq RESTART WITH 1;
    ALTER SEQUENCE {}_id_seq RESTART WITH 1;
    \'"
    """
    formatted_id_reset = id_reset_cmd.format(
        os.getenv("POSTGRES_USERNAME"),
        os.getenv("SUPERSET_METADATA_PORT"),
        "dashboards",
        "slices",
        "tables",
        "dbs",
    )
    command = ["docker-compose", "exec", "dashboard-metadata", formatted_id_reset]
    _, error = subprocess.Popen(
        command,
        shell=True,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate(os.getenv("POSGTRES_PASSWORD"))
    assert len(error) == 0
