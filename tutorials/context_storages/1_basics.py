# %% [markdown]
"""
# 1. Basics

The following tutorial shows the basic use of the database connection.

See %mddoclink(api,context_storages.database,context_storage_factory) function
for creating a context storage by path.

In this example JSON file is used as a storage.
"""

# %pip install dff[json,pickle]

# %%
import pathlib

from dff.context_storages import context_storage_factory

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import TOY_SCRIPT_ARGS, HAPPY_PATH

pathlib.Path("dbs").mkdir(exist_ok=True)
db = context_storage_factory("json://dbs/file.json")
# db = context_storage_factory("pickle://dbs/file.pkl")
# db = context_storage_factory("shelve://dbs/file")

pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    # a function for automatic tutorial running (testing) with HAPPY_PATH

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
