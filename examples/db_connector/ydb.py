"""
1. YDB
======
"""

import logging
import os

from dff.core.engine.core import Actor

from dff.connectors.db import connector_factory
from _db_connector_utils import script, run_auto_mode, run_interactive_mode
from examples.utils import get_auto_arg

logger = logging.getLogger(__name__)


actor = Actor(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))

# ##### Connecting to yandex cloud
# https://github.com/zinal/ydb-python-sdk/blob/ex_basic-example_p1/examples/basic_example_v1/README.md
# export YDB_SERVICE_ACCOUNT_KEY_FILE_CREDENTIALS=$HOME/key-ydb-sa-0.json
# export YDB_ENDPOINT=grpcs://ydb.serverless.yandexcloud.net:2135
# export YDB_DATABASE=/ru-central1/qwertyuiopasdfgh/123456789qwertyui
# ##### or use local-ydb with variables from .env_file

# db_uri="grpc://localhost:2136/local"
db_uri = "{}{}".format(
    os.getenv("YDB_ENDPOINT"),
    os.getenv("YDB_DATABASE"),
)
db = connector_factory(db_uri)


if __name__ == "__main__":
    if get_auto_arg():
        run_auto_mode(actor, db, logger)
    else:
        run_interactive_mode(actor, db, logger)
