"""
1. YDB
======
"""

import os

from dff.connectors.db import connector_factory

from dff.core.pipeline import Pipeline
from dff.utils.testing.common import check_happy_path, run_interactive_mode, is_interactive_mode
from dff.utils.testing.toy_script import TOY_SCRIPT, HAPPY_PATH


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

pipeline = Pipeline.from_script(
    TOY_SCRIPT,
    context_storage=db,
    start_label=("greeting_flow", "start_node"),
    fallback_label=("greeting_flow", "fallback_node"),
)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():  # TODO: Add comments about DISABLE_INTERACTIVE_MODE variable
        run_interactive_mode(pipeline)
