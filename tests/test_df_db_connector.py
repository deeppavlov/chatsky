import pytest
import socket
import os
from platform import system

from df_engine.core.context import Context

from df_db_connector import JSONConnector
from df_db_connector import PickleConnector
from df_db_connector import DBConnector, DBAbstractConnector
from df_db_connector import SQLConnector, postgres_available, mysql_available, sqlite_available
from df_db_connector import connector_factory


def ping_localhost(port: int, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("localhost", port))
    except OSError as error:
        return False
    else:
        s.close()
        return True


POSTGRES_ACTIVE = ping_localhost(5432)

MYSQL_ACTIVE = ping_localhost(3307)


def generic_test(connector_instance, testing_context, testing_telegram_id):
    assert isinstance(connector_instance, DBConnector)
    assert isinstance(connector_instance, DBAbstractConnector)
    # perform cleanup
    connector_instance.clear()
    assert len(connector_instance) == 0
    # test write operations
    connector_instance[testing_telegram_id] = {"foo": "bar", "baz": "qux"}
    assert testing_telegram_id in connector_instance
    assert len(connector_instance) == 1
    connector_instance[testing_telegram_id] = testing_context  # overwriting a key
    assert len(connector_instance) == 1
    # test read operations
    new_ctx = connector_instance[testing_telegram_id]
    assert isinstance(new_ctx, Context)
    assert new_ctx.dict() == testing_context.dict()
    # test delete operations
    del connector_instance[testing_telegram_id]
    assert testing_telegram_id not in connector_instance
    # test `get` method
    assert connector_instance.get(testing_telegram_id) is None


def test_main(testing_file, testing_context, testing_telegram_id):
    assert issubclass(DBConnector, DBAbstractConnector)
    connector_instance = connector_factory(f"json://{testing_file}")
    generic_test(connector_instance, testing_context, testing_telegram_id)


def test_json(testing_file, testing_context, testing_telegram_id):
    connector_instance = JSONConnector(f"json://{testing_file}")
    generic_test(connector_instance, testing_context, testing_telegram_id)


def test_pickle(testing_file, testing_context, testing_telegram_id):
    connector_instance = PickleConnector(f"pickle://{testing_file}")
    generic_test(connector_instance, testing_context, testing_telegram_id)


@pytest.mark.skipif(POSTGRES_ACTIVE == False, reason="Postgres server not running")
@pytest.mark.skipif(postgres_available == False, reason="Postgres dependencies missing")
def test_postgres(testing_context, testing_telegram_id):
    connector_instance = SQLConnector(
        "postgresql://{}:{}@localhost:5432/{}".format(os.getenv("PG_USERNAME"), os.getenv("PG_PASSWORD"), "test")
    )
    generic_test(connector_instance, testing_context, testing_telegram_id)


@pytest.mark.skipif(sqlite_available == False, reason="Sqlite dependencies missing")
def test_sqlite(testing_file, testing_context, testing_telegram_id):
    separator = "///" if system() == "Windows" else "////"
    connector_instance = SQLConnector(f"sqlite:{separator}{testing_file}")

    generic_test(connector_instance, testing_context, testing_telegram_id)


@pytest.mark.skipif(MYSQL_ACTIVE == False, reason="Mysql server not running")
@pytest.mark.skipif(mysql_available == False, reason="Mysql dependencies missing")
def test_mysql(testing_context, testing_telegram_id):
    connector_instance = SQLConnector(
        "mysql+pymysql://{}:{}@localhost:3307/{}".format(
            os.getenv("MYSQL_USERNAME"), os.getenv("MYSQL_PASSWORD"), "test"
        )
    )
    generic_test(connector_instance, testing_context, testing_telegram_id)
