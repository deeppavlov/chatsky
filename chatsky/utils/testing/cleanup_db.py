"""
Cleanup DB
----------
This module defines functions that allow to delete data in various types of databases,
including JSON, MongoDB, Pickle, Redis, Shelve, SQL, and YDB databases.
"""

from chatsky.context_storages import (
    JSONContextStorage,
    MongoContextStorage,
    RedisContextStorage,
    SQLContextStorage,
    YDBContextStorage,
    mongo_available,
    redis_available,
    sqlite_available,
    postgres_available,
    mysql_available,
    ydb_available,
)


async def delete_file(storage: JSONContextStorage):
    """
    Delete all data from a JSON context storage.

    :param storage: A JSONContextStorage object.
    """
    if storage.path.exists():
        storage.path.unlink()


async def delete_mongo(storage: MongoContextStorage):
    """
    Delete all data from a MongoDB context storage.

    :param storage: A MongoContextStorage object
    """
    if not mongo_available:
        raise Exception("Can't delete mongo database - mongo provider unavailable!")
    for collection in [storage._main_table, storage._turns_table, storage._misc_table]:
        await collection.drop()


async def delete_redis(storage: RedisContextStorage):
    """
    Delete all data from a Redis context storage.

    :param storage: A RedisContextStorage object.
    """
    if not redis_available:
        raise Exception("Can't delete redis database - redis provider unavailable!")
    await storage.clear_all()
    await storage._redis.close()


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
    async with storage.engine.begin() as conn:
        for table in [storage._main_table, storage._turns_table, storage._misc_table]:
            await conn.run_sync(table.drop, storage.engine)


async def delete_ydb(storage: YDBContextStorage):
    """
    Delete all data from a YDB context storage.

    :param storage: A YDBContextStorage object.
    """
    if not ydb_available:
        raise Exception("Can't delete ydb database - ydb provider unavailable!")

    async def callee(session):
        for field in [storage._CONTEXTS_TABLE, storage._LOGS_TABLE]:
            await session.drop_table("/".join([storage.database, f"{storage.table_prefix}_{field}"]))

    await storage.pool.retry_operation(callee)
