# %% [markdown]
"""
# 4. Redis

This is an example of using Redis.
"""


# %%
import os

from dff.connectors.db import connector_factory

from dff.core.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH


# %%
db_uri = "redis://{}:{}@localhost:6379/{}".format("", os.getenv("REDIS_PASSWORD"), "0")
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
