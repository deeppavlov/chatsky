import os
import pytest
from sqlalchemy import text

from dff.stats import make_saver
from dff.stats.savers.clickhouse import ClickHouseSaver
from dff.stats.savers.postgresql import PostgresSaver

from tests.db_list import POSTGRES_ACTIVE, CLICKHOUSE_ACTIVE

POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB")


@pytest.mark.skipif(not POSTGRES_ACTIVE, reason="Postgres server is not running")
@pytest.mark.skipif(not all([POSTGRES_USERNAME, POSTGRES_PASSWORD, POSTGRES_DB]), reason="Postgres credentials missing")
@pytest.mark.asyncio
async def test_PG_saving(table, testing_items):
    PG_uri_string = "postgresql://{}:{}@localhost:5432/{}".format(POSTGRES_USERNAME, POSTGRES_PASSWORD, POSTGRES_DB)
    saver: PostgresSaver = make_saver(PG_uri_string, table=table)
    await saver._create_table()

    async with saver.engine.connect() as conn:
        await conn.execute(text(f"TRUNCATE {table}"))
        await conn.commit()

    await saver.save(testing_items)
    await saver.save(testing_items)

    async with saver.engine.connect() as conn:
        result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        first = result.first()

    result_2 = await saver.load()
    assert len(result_2) == (len(testing_items) * 2)
    assert int(first[0]) == (len(testing_items) * 2)


@pytest.mark.skipif(not CLICKHOUSE_ACTIVE, reason="Clickhouse server is not running")
@pytest.mark.skipif(
    not all([CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DB]), reason="Clickhouse credentials missing"
)
@pytest.mark.asyncio
async def test_CH_saving(table, testing_items):
    CH_uri_string = "clickhouse://{}:{}@localhost:8123/{}".format(CLICKHOUSE_USER, CLICKHOUSE_PASSWORD, CLICKHOUSE_DB)
    saver: ClickHouseSaver = make_saver(CH_uri_string, table=table)
    await saver._create_table()

    await saver.ch_client.execute(f"TRUNCATE {table}")

    await saver.save(testing_items)
    await saver.save(testing_items)

    result = await saver.ch_client.fetchval(f"SELECT COUNT (*) FROM {table}")
    result_2 = await saver.load()
    assert len(result_2) == (len(testing_items) * 2)
    assert int(result) == (len(testing_items) * 2)
