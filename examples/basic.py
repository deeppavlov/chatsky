import logging
import pathlib

from df_engine.core import Actor

from df_db_connector import connector_factory
from .utils import run_actor, script

logger = logging.getLogger(__name__)

actor = Actor(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))

pathlib.Path("dbs").mkdir(exist_ok=True)
db = connector_factory("json://dbs/file.json")
# db = connector_factory("pickle://dbs/file.pkl")
# db = connector_factory("shelve://dbs/file")
# db = connector_factory("shelve://dbs/file")


def main(actor):
    while True:
        in_request = input("type your answer: ")
        run_actor(in_request, actor, db)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s-%(name)15s:%(lineno)3s:%(funcName)20s():%(levelname)s - %(message)s", level=logging.INFO
    )
    main(actor)
