import logging
import pathlib
import os

from df_engine.core import Actor

from df_db_connector import connector_factory
from .utils import run_actor, script

logger = logging.getLogger(__name__)

actor = Actor(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))

######### mongodb #########
# db_uri = "mongodb://{}:{}@localhost:27017/{}".format(
#     os.getenv("MONGO_INITDB_ROOT_USERNAME"),
#     os.getenv("MONGO_INITDB_ROOT_PASSWORD"),
#     os.getenv("MONGO_INITDB_ROOT_USERNAME"),
# )

######### redis #########
# db_uri = "redis://{}:{}@localhost:6379/{}".format("", os.getenv("REDIS_PASSWORD"), "0")

######### sqlite #########
# from platform import system
# pathlib.Path("dbs").mkdir(exist_ok=True)
# separator = "///" if system() == "Windows" else "////"
# db_uri = f"sqlite:{separator}dbs/sqlite.db"

######### mysql #########
# db_uri = "mysql+pymysql://{}:{}@localhost:3307/{}".format(
#     os.getenv("MYSQL_USERNAME"),
#     os.getenv("MYSQL_PASSWORD"),
#     os.getenv("MYSQL_DATABASE"),
# )

######### postgresql #########
db_uri = "postgresql://{}:{}@localhost:5432/{}".format(
    os.getenv("POSTGRES_USERNAME"),
    os.getenv("POSTGRES_PASSWORD"),
    os.getenv("POSTGRES_DB"),
)
db = connector_factory(db_uri)


def main(actor):
    while True:
        in_request = input("type your answer: ")
        run_actor(in_request, actor, db)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s", level=logging.INFO
    )
    main(actor)
