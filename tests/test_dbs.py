import pytest
import socket
import os
from platform import system

from df_engine.core.context import Context

from df_db_connector.json_connector import JSONConnector
from df_db_connector.pickle_connector import PickleConnector
from df_db_connector.shelve_connector import ShelveConnector
from df_db_connector.db_connector import DBConnector, DBAbstractConnector
from df_db_connector.sql_connector import SQLConnector, postgres_available, mysql_available, sqlite_available
from df_db_connector.redis_connector import RedisConnector, redis_available
from df_db_connector.mongo_connector import MongoConnector, mongo_available
from df_db_connector.ydb_connector import YDBConnector, ydb_available
from df_db_connector import connector_factory


def ping_localhost(port: int, timeout=60):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", port))
    except OSError as error:
        return False
    else:
        s.close()
        return True


MONGO_ACTIVE = ping_localhost(27017)

REDIS_ACTIVE = ping_localhost(6379)

POSTGRES_ACTIVE = ping_localhost(5432)

MYSQL_ACTIVE = ping_localhost(3307)

YDB_ACTIVE = ping_localhost(2136)


def generic_test(connector_instance, testing_context, context_id):
    assert isinstance(connector_instance, DBConnector)
    assert isinstance(connector_instance, DBAbstractConnector)
    # perform cleanup
    connector_instance.clear()
    assert len(connector_instance) == 0
    # test write operations
    connector_instance[context_id] = Context(id=context_id)
    assert context_id in connector_instance
    assert len(connector_instance) == 1
    connector_instance[context_id] = testing_context  # overwriting a key
    assert len(connector_instance) == 1
    # test read operations
    new_ctx = connector_instance[context_id]
    assert isinstance(new_ctx, Context)
    assert {**new_ctx.dict(), "id": str(new_ctx.id)} == {**testing_context.dict(), "id": str(testing_context.id)}
    # test delete operations
    del connector_instance[context_id]
    assert context_id not in connector_instance
    # test `get` method
    assert connector_instance.get(context_id) is None


def test_main(testing_file, testing_context, context_id):
    assert issubclass(DBConnector, DBAbstractConnector)
    connector_instance = connector_factory(f"json://{testing_file}")
    generic_test(connector_instance, testing_context, context_id)


def test_shelve(testing_file, testing_context, context_id):
    connector_instance = ShelveConnector(f"shelve://{testing_file}")
    generic_test(connector_instance, testing_context, context_id)


def test_json(testing_file, testing_context, context_id):
    connector_instance = JSONConnector(f"json://{testing_file}")
    generic_test(connector_instance, testing_context, context_id)


def test_pickle(testing_file, testing_context, context_id):
    connector_instance = PickleConnector(f"pickle://{testing_file}")
    generic_test(connector_instance, testing_context, context_id)


@pytest.mark.skipif(MONGO_ACTIVE == False, reason="Mongodb server is not running")
@pytest.mark.skipif(mongo_available == False, reason="Mongodb dependencies missing")
def test_mongo(testing_context, context_id):
    if system() == "Windows":
        pytest.skip()

    connector_instance = MongoConnector(
        "mongodb://{}:{}@localhost:27017/{}".format(
            os.getenv("MONGO_INITDB_ROOT_USERNAME"),
            os.getenv("MONGO_INITDB_ROOT_PASSWORD"),
            os.getenv("MONGO_INITDB_ROOT_USERNAME"),
        )
    )
    generic_test(connector_instance, testing_context, context_id)


@pytest.mark.skipif(REDIS_ACTIVE == False, reason="Redis server is not running")
@pytest.mark.skipif(redis_available == False, reason="Redis dependencies missing")
def test_redis(testing_context, context_id):
    connector_instance = RedisConnector("redis://{}:{}@localhost:6379/{}".format("", os.getenv("REDIS_PASSWORD"), "0"))
    generic_test(connector_instance, testing_context, context_id)


@pytest.mark.skipif(POSTGRES_ACTIVE == False, reason="Postgres server is not running")
@pytest.mark.skipif(postgres_available == False, reason="Postgres dependencies missing")
def test_postgres(testing_context, context_id):
    connector_instance = SQLConnector(
        "postgresql://{}:{}@localhost:5432/{}".format(
            os.getenv("POSTGRES_USERNAME"),
            os.getenv("POSTGRES_PASSWORD"),
            os.getenv("POSTGRES_DB"),
        )
    )
    generic_test(connector_instance, testing_context, context_id)


@pytest.mark.skipif(sqlite_available == False, reason="Sqlite dependencies missing")
def test_sqlite(testing_file, testing_context, context_id):
    separator = "///" if system() == "Windows" else "////"
    connector_instance = SQLConnector(f"sqlite:{separator}{testing_file}")

    generic_test(connector_instance, testing_context, context_id)


@pytest.mark.skipif(MYSQL_ACTIVE == False, reason="Mysql server is not running")
@pytest.mark.skipif(mysql_available == False, reason="Mysql dependencies missing")
def test_mysql(testing_context, context_id):
    connector_instance = SQLConnector(
        "mysql+pymysql://{}:{}@localhost:3307/{}".format(
            os.getenv("MYSQL_USERNAME"),
            os.getenv("MYSQL_PASSWORD"),
            os.getenv("MYSQL_DATABASE"),
        )
    )
    generic_test(connector_instance, testing_context, context_id)


@pytest.mark.skipif(YDB_ACTIVE == False, reason="YQL server not running")
@pytest.mark.skipif(ydb_available == False, reason="YDB dependencies missing")
def test_ydb(testing_context, context_id):
    connector_instance = YDBConnector(f'{os.getenv("YDB_ENDPOINT")}{os.getenv("YDB_DATABASE")}', "test")
    generic_test(connector_instance, testing_context, context_id)
