"""
Cleanup DB
----------
This module defines functions that allow to delete data in various types of databases,
including JSON, MongoDB, Pickle, Redis, Shelve, SQL, and YDB databases.
"""
import os

from dff.context_storages import (
    JSONContextStorage,
    MongoContextStorage,
    PickleContextStorage,
    RedisContextStorage,
    ShelveContextStorage,
    SQLContextStorage,
    YDBContextStorage,
    json_available,
    mongo_available,
    pickle_available,
    redis_available,
    sqlite_available,
    postgres_available,
    mysql_available,
    ydb_available,
)


async def delete_json(storage: JSONContextStorage):
    """
    Delete all data from a JSON context storage.

    :param storage: A JSONContextStorage object.
    """
    if not json_available:
        raise Exception("Can't delete JSON database - JSON provider unavailable!")
    if os.path.isfile(storage.path):
        os.remove(storage.path)


async def delete_mongo(storage: MongoContextStorage):
    """
    Delete all data from a MongoDB context storage.

    :param storage: A MongoContextStorage object
    """
    if not mongo_available:
        raise Exception("Can't delete mongo database - mongo provider unavailable!")
    await storage.collection.drop()


async def delete_pickle(storage: PickleContextStorage):
    """
    Delete all data from a Pickle context storage.

    :param storage: A PickleContextStorage object.
    """
    if not pickle_available:
        raise Exception("Can't delete pickle database - pickle provider unavailable!")
    if os.path.isfile(storage.path):
        os.remove(storage.path)


async def delete_redis(storage: RedisContextStorage):
    """
    Delete all data from a Redis context storage.

    :param storage: A RedisContextStorage object.
    """
    if not redis_available:
        raise Exception("Can't delete redis database - redis provider unavailable!")
    await storage.clear_async()


async def delete_shelve(storage: ShelveContextStorage):
    """
    Delete all data from a Shelve context storage.

    :param storage: A ShelveContextStorage object.
    """
    if os.path.isfile(storage.path):
        os.remove(storage.path)


async def delete_sql(storage: SQLContextStorage):
    """
    Delete all data from an SQL context storage.

    :param storage: An SQLContextStorage object.
    """
    if storage.dialect == "postgres" and not postgres_available:
        raise Exception("Can't delete postgres database - postgres provider unavailable!")
    if storage.dialect == "sqlite" and not sqlite_available:
        raise Exception("Can't delete sqlite database - sqlite provider unavailable!")
    if storage.dialect == "mysql" and not mysql_available:
        raise Exception("Can't delete mysql database - mysql provider unavailable!")
    async with storage.engine.connect() as conn:
        await conn.run_sync(storage.table.drop, storage.engine)


async def delete_ydb(storage: YDBContextStorage):
    """
    Delete all data from a YDB context storage.

    :param storage: A YDBContextStorage object.
    """
    if not ydb_available:
        raise Exception("Can't delete ydb database - ydb provider unavailable!")

    async def callee(session):
        await session.drop_table("/".join([storage.database, storage.table_name]))

    await storage.pool.retry_operation(callee)
