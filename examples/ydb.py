import logging
import os

from df_engine.core import Actor

from df_db_connector import connector_factory
from .utils import run_actor, script

logger = logging.getLogger(__name__)


actor = Actor(script, start_label=("greeting_flow", "start_node"), fallback_label=("greeting_flow", "fallback_node"))

###### Connecting to yandex cloud
# https://github.com/zinal/ydb-python-sdk/blob/ex_basic-example_p1/examples/basic_example_v1/README.md
# export YDB_SERVICE_ACCOUNT_KEY_FILE_CREDENTIALS=$HOME/key-ydb-sa-0.json
# export YDB_ENDPOINT=grpcs://ydb.serverless.yandexcloud.net:2135
# export YDB_DATABASE=/ru-central1/qwertyuiopasdfgh/123456789qwertyui
###### or use local-ydb with variables from .env_file

# db_uri="grpc://localhost:2136/local"
db_uri = "{}{}".format(
    os.getenv("YDB_ENDPOINT"),
    os.getenv("YDB_DATABASE"),
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
