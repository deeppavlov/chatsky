# %% [markdown]
"""
# 5. MySQL

This is a tutorial on using MySQL.

See %mddoclink(api,context_storages.sql,SQLContextStorage) class
for storing you users' contexts in SQL databases.

DFF uses [sqlalchemy](https://docs.sqlalchemy.org/en/20/)
and [asyncmy](https://github.com/long2ice/asyncmy)
libraries for asynchronous access to MySQL DB.
"""

# %pip install dff[mysql]

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
db_uri = "mysql+asyncmy://{}:{}@localhost:3307/{}".format(
    os.environ["MYSQL_USERNAME"],
    os.environ["MYSQL_PASSWORD"],
    os.environ["MYSQL_DATABASE"],
)
db = context_storage_factory(db_uri)


pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
