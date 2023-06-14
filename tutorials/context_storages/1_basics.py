# %% [markdown]
"""
# 1. Basics

The following tutorial shows the basic use of the database connection.
"""


# %%
import pathlib

from dff.context_storages import context_storage_factory
from dff.context_storages.context_schema import SchemaFieldReadPolicy, SchemaFieldWritePolicy

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import TOY_SCRIPT_ARGS, HAPPY_PATH

pathlib.Path("dbs").mkdir(exist_ok=True)
db = context_storage_factory("json://dbs/file.json")
# db = context_storage_factory("pickle://dbs/file.pkl")
# db = context_storage_factory("shelve://dbs/file.shlv")

pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)

# Scheme field subscriptcan be changed:
# that will mean that only these MISC keys will be read and written
db.context_schema.misc.subscript = ["some_key", "some_other_key"]

# Scheme field subscriptcan be changed:
# that will mean that only last REQUESTS will be read and written
db.context_schema.requests.subscript = -5

# The default policy for reading is `SchemaFieldReadPolicy.READ` -
# the values will be read
# However, another possible policy option is `SchemaFieldReadPolicy.IGNORE` -
# the values will be ignored
db.context_schema.responses.on_read = SchemaFieldReadPolicy.IGNORE

# The default policy for writing values is `SchemaFieldReadPolicy.UPDATE` -
# the value will be updated
# However, another possible policy options are `SchemaFieldReadPolicy.IGNORE` -
# the value will be ignored
# `SchemaFieldReadPolicy.HASH_UPDATE` and `APPEND` are also possible,
# but they will be described together with writing dictionaries
db.context_schema.created_at.on_write = SchemaFieldWritePolicy.IGNORE

# The default policy for writing dictionaries is `SchemaFieldReadPolicy.UPDATE_HASH`
# - the values will be updated only if they have changed since the last time they were read
# However, another possible policy option is `SchemaFieldReadPolicy.APPEND`
# - the values will be updated if only they are not present in database
db.context_schema.framework_states.on_write = SchemaFieldWritePolicy.APPEND

# Some field properties can't be changed: these are `storage_key` and `active_ctx`
try:
    db.context_schema.storage_key.on_write = SchemaFieldWritePolicy.IGNORE
    raise RuntimeError("Shouldn't reach here without an error!")
except TypeError:
    pass

# Another important note: `name` property on neild can **never** be changed
try:
    db.context_schema.active_ctx.on_read = SchemaFieldReadPolicy.IGNORE
    raise RuntimeError("Shouldn't reach here without an error!")
except TypeError:
    pass

new_db = context_storage_factory("json://dbs/file.json")
pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=new_db)

if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    # This is a function for automatic tutorial running (testing) with HAPPY_PATH

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
