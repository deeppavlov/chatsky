# %% [markdown]
"""
# 7. Yandex DataBase

This is a tutorial on how to use Yandex DataBase.

See %mddoclink(api,context_storages.ydb,YDBContextStorage) class
for storing you users' contexts in Yandex database.

DFF uses [ydb.aio](https://ydb.tech/en/docs/)
library for asynchronous access to Yandex DB.
"""

# %pip install dff[ydb]

# %%
import os

from dff.context_storages import context_storage_factory

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    run_interactive_mode,
    is_interactive_mode,
)
from dff.utils.testing.toy_script import TOY_SCRIPT_ARGS, HAPPY_PATH


# %%
# ##### Connecting to yandex cloud
# https://github.com/zinal/ydb-python-sdk/blob/ex_basic-example_p1/examples/basic_example_v1/README.md
# export YDB_SERVICE_ACCOUNT_KEY_FILE_CREDENTIALS=$HOME/key-ydb-sa-0.json
# export YDB_ENDPOINT=grpcs://ydb.serverless.yandexcloud.net:2135
# export YDB_DATABASE=/ru-central1/qwertyuiopasdfgh/123456789qwertyui
# ##### or use local-ydb with variables from .env_file
# db_uri="grpc://localhost:2136/local"

db_uri = "{}{}".format(
    os.environ["YDB_ENDPOINT"],
    os.environ["YDB_DATABASE"],
)
db = context_storage_factory(db_uri)

pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    if is_interactive_mode():
        run_interactive_mode(pipeline)
