# -*- coding: utf-8 -*-
# flake8: noqa: F401

__author__ = "Denis Kuznetsov"
__email__ = "kuznetosv.den.p@gmail.com"
__version__ = "0.2.1"

import importlib

from .db_connector import DBAbstractConnector, DBConnector, threadsafe_method
from .json_connector import JSONConnector
from .pickle_connector import PickleConnector
from .sql_connector import SQLConnector
from .ydb_connector import YDBConnector
from .redis_connector import RedisConnector
from .mongo_connector import MongoConnector

SUPPORTED_PROTOCOLS = {
    "shelve": {
        "module": "shelve_connector",
        "class": "ShelveConnector",
        "uri_example": "shelve://path_to_the_file/file_name",
    },
    "json": {
        "module": "json_connector",
        "class": "JSONConnector",
        "uri_example": "json://path_to_the_file/file_name",
    },
    "pickle": {
        "module": "pickle_connector",
        "class": "PickleConnector",
        "uri_example": "pickle://path_to_the_file/file_name",
    },
    "sqlite": {
        "module": "sql_connector",
        "class": "SQLConnector",
        "uri_example": "sqlite://path_to_the_file/file_name",
    },
    "redis": {
        "module": "redis_connector",
        "class": "RedisConnector",
        "uri_example": "redis://:pass@localhost:6379/0",
    },
    "mongodb": {
        "module": "mongo_connector",
        "class": "MongoConnector",
        "uri_example": "mongodb://admin:pass@localhost:27017/admin",
    },
    "mysql": {
        "module": "sql_connector",
        "class": "SQLConnector",
        "uri_example": "mysql+pymysql://root:pass@localhost:3307/test",
    },
    "postgresql": {
        "module": "sql_connector",
        "class": "SQLConnector",
        "uri_example": "postgresql://postgres:pass@localhost:5432/test",
    },
    "grpc": {
        "module": "ydb_connector",
        "class": "YDBConnector",
        "uri_example": "grpc://localhost:2136/local",
    },
    "grpcs": {
        "module": "ydb_connector",
        "class": "YDBConnector",
        "uri_example": "grpcs://localhost:2135/local",
    },
}


def connector_factory(path: str, **kwargs):
    """
    Use connector_factory to lazy import connector types and instantiate them.
    The function takes a database connection URI or its equivalent. It should be prefixed with database name,
    followed by the symbol triplet '://'.
    Then, you should list the connection parameters like this: user:password@host:port/database
    The whole URI will then look like this:
    - shelve://path_to_the_file/file_name
    - json://path_to_the_file/file_name
    - pickle://path_to_the_file/file_name
    - sqlite://path_to_the_file/file_name
    - redis://:pass@localhost:6379/0
    - mongodb://admin:pass@localhost:27017/admin
    - mysql+pymysql://root:pass@localhost:3307/test
    - postgresql://postgres:pass@localhost:5432/test
    - grpc://localhost:2136/local
    - grpcs://localhost:2135/local

    For connectors that write to local files, the function expects a file path instead of connection params:
    json://file.json
    When using sqlite backend your prefix should contain three slashes if you use Windows, or four in other cases.
    sqlite:////file.db
    If you want to use additional parameters in class constructors, you can pass them to this function as kwargs.

    """
    prefix, _, _ = path.partition("://")
    if "sql" in prefix:
        prefix = prefix.split("+")[0]  # this takes care of alternative sql drivers
    assert (
        prefix in SUPPORTED_PROTOCOLS
    ), f"""
    URI path should be prefixed with one of the following:\n
    {", ".join(SUPPORTED_PROTOCOLS.keys())}.\n
    For more information, see the function doc:\n{connector_factory.__doc__}
    """
    _class, module = SUPPORTED_PROTOCOLS[prefix]["class"], SUPPORTED_PROTOCOLS[prefix]["module"]
    target_class = getattr(importlib.import_module(f".{module}", package="df_db_connector"), _class)
    return target_class(path, **kwargs)
