"""
1. Basics
=========
"""

import logging
import pathlib

from dff.core.engine.core import Actor

from dff.connectors.db import connector_factory
from dff._example_utils.db_connector import run_auto_mode, run_interactive_mode
from dff._example_utils.index import is_in_notebook, SCRIPT

logger = logging.getLogger(__name__)

actor = Actor(SCRIPT, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))

pathlib.Path("dbs").mkdir(exist_ok=True)
db = connector_factory("json://dbs/file.json")
# db = connector_factory("pickle://dbs/file.pkl")
# db = connector_factory("shelve://dbs/file")
# db = connector_factory("shelve://dbs/file")


if __name__ == "__main__":
    if is_in_notebook():
        run_auto_mode(actor, db, logger)
    else:
        run_interactive_mode(actor, db, logger)
