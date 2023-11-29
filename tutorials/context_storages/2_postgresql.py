# %% [markdown]
"""
# 2. PostgreSQL

This is a tutorial on using PostgreSQL.

See %mddoclink(api,context_storages.sql,SQLContextStorage) class
for storing your users' contexts in SQL databases.

DFF uses [sqlalchemy](https://docs.sqlalchemy.org/en/20/)
and [asyncpg](https://magicstack.github.io/asyncpg/current/)
libraries for asynchronous access to PostgreSQL DB.
"""

# %pip install dff[postgresql]

# %%
import os

from dff.context_storages import context_storage_factory

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import TOY_SCRIPT_ARGS, HAPPY_PATH


# %%
db_uri = "postgresql+asyncpg://{}:{}@localhost:5432/{}".format(
    os.environ["POSTGRES_USERNAME"],
    os.environ["POSTGRES_PASSWORD"],
    os.environ["POSTGRES_DB"],
)
db = context_storage_factory(db_uri)


pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
