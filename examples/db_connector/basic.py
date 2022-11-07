"""
1. Basics
=========
"""

import logging
import pathlib

from dff.connectors.db import connector_factory
from dff.utils.common import run_example

logger = logging.getLogger(__name__)

pathlib.Path("dbs").mkdir(exist_ok=True)
db = connector_factory("json://dbs/file.json")
# db = connector_factory("pickle://dbs/file.pkl")
# db = connector_factory("shelve://dbs/file")
# db = connector_factory("shelve://dbs/file")


if __name__ == "__main__":
    run_example(logger, context_storage=db)
