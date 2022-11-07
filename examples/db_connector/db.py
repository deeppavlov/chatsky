"""
1. DB
=====
"""

import logging
import os

from dff.connectors.db import connector_factory
from dff.utils.common import run_example

logger = logging.getLogger(__name__)

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
db_uri = "postgresql://{}:{}@localhost:5432/{}".format(
    os.getenv("POSTGRES_USERNAME"),
    os.getenv("POSTGRES_PASSWORD"),
    os.getenv("POSTGRES_DB"),
)
db = connector_factory(db_uri)


if __name__ == "__main__":
    run_example(logger, context_storage=db)
