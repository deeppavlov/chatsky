# %% [markdown]
"""
# 3. MongoDB

This is a tutorial on using MongoDB.
"""


# %%
import os

from dff.context_storages import context_storage_factory

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH


# %%
db_uri = "mongodb://{}:{}@localhost:27017/{}".format(
    os.getenv("MONGO_INITDB_ROOT_USERNAME"),
    os.getenv("MONGO_INITDB_ROOT_PASSWORD"),
    os.getenv("MONGO_INITDB_ROOT_USERNAME"),
)
db = context_storage_factory(db_uri)

pipeline = Pipeline.from_script(
    TOY_SCRIPT,
    context_storage=db,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
