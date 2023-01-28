import os

from dff.context_storages import (
    JSONContextStorage,
    MongoContextStorage,
    PickleContextStorage,
    RedisContextStorage,
    ShelveContextStorage,
    SQLContextStorage,
    YDBContextStorage,
    mongo_available,
    redis_available,
    sqlite_available,
    postgres_available,
    mysql_available,
    ydb_available,
)


async def delete_json(storage: JSONContextStorage):
    if os.path.isfile(storage.path):
        os.remove(storage.path)


async def delete_mongo(storage: MongoContextStorage):
    if not mongo_available:
        raise Exception("Can't delete mongo database - mongo provider unavailable!")
    await storage.collection.drop()


async def delete_pickle(storage: PickleContextStorage):
    if os.path.isfile(storage.path):
        os.remove(storage.path)


async def delete_redis(storage: RedisContextStorage):
    if not redis_available:
        raise Exception("Can't delete redis database - redis provider unavailable!")
    await storage.clear_async()


async def delete_shelve(storage: ShelveContextStorage):
    if os.path.isfile(storage.path):
        os.remove(storage.path)


async def delete_sql(storage: SQLContextStorage):
    if storage.dialect == "postgres" and not postgres_available:
        raise Exception("Can't delete postgres database - postgres provider unavailable!")
    if storage.dialect == "sqlite" and not sqlite_available:
        raise Exception("Can't delete sqlite database - sqlite provider unavailable!")
    if storage.dialect == "mysql" and not mysql_available:
        raise Exception("Can't delete mysql database - mysql provider unavailable!")
    async with storage.engine.connect() as conn:
        await conn.run_sync(storage.table.drop, storage.engine)


async def delete_ydb(storage: YDBContextStorage):
    if not ydb_available:
        raise Exception("Can't delete ydb database - ydb provider unavailable!")

    async def callee(session):
        await session.drop_table("/".join([storage.database, storage.table_name]))

    await storage.pool.retry_operation(callee)
