# %% [markdown]
"""
# 1. Basics

The following example shows the basic use of the database connection.
"""


# %%
import pathlib

from dff.connectors.db import connector_factory

from dff.core.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH

pathlib.Path("dbs").mkdir(exist_ok=True)
db = connector_factory("json://dbs/file.json")
# db = connector_factory("pickle://dbs/file.pkl")
# db = connector_factory("shelve://dbs/file")
# db = connector_factory("shelve://dbs/file")

pipeline = Pipeline.from_script(
    TOY_SCRIPT,
    context_storage=db,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)  # This is a function for automatic example running
    # (testing) with HAPPY_PATH

    # This runs example in interactive mode if not in IPython env
    # + if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs example in interactive mode
