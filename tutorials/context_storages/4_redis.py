# %% [markdown]
"""
# 4. Redis

This is a tutorial on using Redis.

See %mddoclink(api,context_storages.redis,RedisContextStorage) class
for storing you users' contexts in Redis database.

Chatsky uses [redis.asyncio](https://redis.readthedocs.io/en/latest/)
library for asynchronous access to Redis DB.
"""

# %pip install chatsky[redis]

# %%
import os

from chatsky.context_storages import context_storage_factory

from chatsky.pipeline import Pipeline
from chatsky.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from chatsky.utils.testing.toy_script import TOY_SCRIPT_ARGS, HAPPY_PATH


# %%
db_uri = "redis://{}:{}@localhost:6379/{}".format(
    "", os.environ["REDIS_PASSWORD"], "0"
)
db = context_storage_factory(db_uri)


pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
