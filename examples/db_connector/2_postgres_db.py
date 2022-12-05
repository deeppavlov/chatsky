# %% [markdown]
"""
2. DB
=====

"""


# %%
import os

from dff.connectors.db import connector_factory

from dff.core.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, is_interactive_mode, run_interactive_mode
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH


# %%
# ######## mongodb #########
# db_uri = "mongodb://{}:{}@localhost:27017/{}".format(
#     os.getenv("MONGO_INITDB_ROOT_USERNAME"),
#     os.getenv("MONGO_INITDB_ROOT_PASSWORD"),
#     os.getenv("MONGO_INITDB_ROOT_USERNAME"),
# )

# ######## redis #########
# db_uri = "redis://{}:{}@localhost:6379/{}".format("", os.getenv("REDIS_PASSWORD"), "0")

# ######## sqlite #########
# from platform import system
# pathlib.Path("dbs").mkdir(exist_ok=True)
# separator = "///" if system() == "Windows" else "////"
# db_uri = f"sqlite:{separator}dbs/sqlite.db"

# ######## mysql #########
# db_uri = "mysql+pymysql://{}:{}@localhost:3307/{}".format(
#     os.getenv("MYSQL_USERNAME"),
#     os.getenv("MYSQL_PASSWORD"),
#     os.getenv("MYSQL_DATABASE"),
# )

# ######## postgresql #########
#db_uri = "postgresql://{}:{}@localhost:5432/{}".format(
#    os.getenv("POSTGRES_USERNAME"),
#    os.getenv("POSTGRES_PASSWORD"),
#    os.getenv("POSTGRES_DB"),
#)
#db = connector_factory(db_uri)


# %%
# pipeline = Pipeline.from_script(
#     TOY_SCRIPT,
#     context_storage=db,
#     start_label=("greeting_flow", "start_node"),
#     fallback_label=("greeting_flow", "fallback_node"),
# )

# if __name__ == "__main__":
#     check_happy_path(pipeline, HAPPY_PATH)
#     if is_interactive_mode():
#         run_interactive_mode(pipeline)
