# %% [markdown]
"""
# 8. Partial context updates

The following tutorial shows the advanced usage of context storage and context storage schema.
"""

# %pip install dff

# %%
import pathlib

from dff.context_storages import (
    context_storage_factory,
    ALL_ITEMS,
)

from dff.pipeline import Pipeline
from dff.utils.testing.common import (
    check_happy_path,
    is_interactive_mode,
    run_interactive_mode,
)
from dff.utils.testing.toy_script import TOY_SCRIPT_ARGS, HAPPY_PATH

# %%
pathlib.Path("dbs").mkdir(exist_ok=True)
db = context_storage_factory("shelve://dbs/partly.shlv")

pipeline = Pipeline.from_script(*TOY_SCRIPT_ARGS, context_storage=db)

# %% [markdown]
"""

## Context Schema

Context schema is a special object included in any context storage.
This object helps you refining use of context storage, writing fields partially instead
of writing them all at once.

How does that partial field writing work?
In most cases, every context storage operates two "tables", "dictionaries", "files", etc.
One of them is called CONTEXTS and contains serialized context values, including
last few (the exact number is controlled by context schema `subscript` property)
dictionaries with integer keys (that are `requests`, `responses` and `labels`) items.
The other is called LOGS and contains all the other items (not the most recent ones).

Values from CONTEXTS table are read frequently and are not so numerous.
Values from LOGS table are written frequently, but are almost never read.
"""

# %% [markdown]
"""

## `ContextStorage` fields

Take a look at fields of ContextStorage, whose names match the names of Context fields.
There are three of them: `requests`, `responses` and `labels`, i.e. dictionaries
with integer keys.
"""

# %%
# These fields have two properties, first of them is `name`
# (it matches field name and can't be changed).
print(db.context_schema.requests.name)

# %% [markdown]
"""
The fields also contain `subscript` property:
this property controls the number of *last* dictionary items that will be read and written
(the items are ordered by keys, ascending) - default value is 3.
In order to read *all* items at once the property can also be set to "__all__" literal
(it can also be imported as constant).
"""

# %%
# All items will be read and written.
db.context_schema.requests.subscript = ALL_ITEMS

# %%
# 5 last items will be read and written.
db.context_schema.requests.subscript = 5

# %% [markdown]
"""
There are also some boolean field flags that worth attention.
Let's take a look at them:
"""

# %%
# `append_single_log` if set will *not* write only one value to LOGS table each turn.
# I.e. only the values that are not written to CONTEXTS table anymore will be written to LOGS.
# It is True by default.
db.context_schema.append_single_log = True

# %%
# `duplicate_context_in_logs` if set will *always* backup all items in CONTEXT table in LOGS table.
# I.e. all the fields that are written to CONTEXT tables will be always backed up to LOGS.
# It is False by default.
db.context_schema.duplicate_context_in_logs = False

# %%
# `supports_async` if set will try to perform *some* operations asynchroneously.
# It is set automatically for different context storages to True or False according to their
# capabilities. You should change it only if you use some external DB distribution that was not
# tested by DFF development team.
# NB! Here it is set to True because we use pickle context storage, backed up be `aiofiles` library.
db.context_schema.supports_async = True


# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    # This is a function for automatic tutorial running (testing) with HAPPY_PATH

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        run_interactive_mode(pipeline)  # This runs tutorial in interactive mode
