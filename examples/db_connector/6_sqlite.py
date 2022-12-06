# %% [markdown]
"""
# 6. SQLite

"""


# %%
# pip install dff  # Uncomment this line to install the framework


# %%
import pathlib

from dff.connectors.db import connector_factory

from dff.core.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, is_interactive_mode, run_interactive_mode
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH


# %%
from platform import system
pathlib.Path("dbs").mkdir(exist_ok=True)
separator = "///" if system() == "Windows" else "////"
db_uri = f"sqlite:{separator}dbs/sqlite.db"
db = connector_factory(db_uri)


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
