# %% [markdown]
"""
# 8. Partial context updates

The following tutorial shows the advanced usage
of context storage and context storage schema.
"""

# %pip install chatsky

# %%
from pathlib import Path

from chatsky import Pipeline
from chatsky.context_storages import context_storage_factory
from chatsky.context_storages.database import NameConfig
from chatsky.utils.testing.common import check_happy_path, is_interactive_mode
from chatsky.utils.testing.toy_script import TOY_SCRIPT_KWARGS, HAPPY_PATH

# %%
Path("dbs").mkdir(exist_ok=True)
db = context_storage_factory("shelve://dbs/partly.shlv")

pipeline = Pipeline(**TOY_SCRIPT_KWARGS, context_storage=db)

# %% [markdown]
"""
Most of the `Context` fields, that might grow in size uncontrollably,
are stored in a special structure, `ContextDict`.
This structure can be used for fine-grained access to the underlying
database, partial and asynchronous element loading.
In particular, this is relevant for `labels`, `requests` and `responses`
fields, while `misc` and `framework_data` are always loaded
completely and synchronously.

How does that partial field writing work?
In most cases, every context storage
operates two "tables", "dictionaries", "files", etc.
One of them is called `MAIN` and contains all the "primitive" `Context`
data (and also the data that will be read and written completely every time,
serialized) - that includes context `id`, `current_turn_id`, `_created_at`,
`_updated_at`, `misc` and `framework_data` fields.
The other one is called `TURNS` and contains triplets of the data generated on
each conversation step: `label`, `request` and `response`.

Whenever a context is loaded, only one item from `MAIN` teble
and zero to few items from `TURNS` table are loaded synchronously.
More items from `TURNS` table can be loaded later asynchronously on demand.
"""

# %% [markdown]
"""
Database table layout and default behavior is controlled by
some special fields of the `DBContextStorage` class.

All the table and field names are stored in a special `NameConfig`
static class.
"""

# %%
print(
    {
        k: v
        for k, v in vars(NameConfig).items()
        if not k.startswith("__") and not callable(v)
    }
)

# %% [markdown]
"""
Another property worth mentioning is `_subscripts`:
this property controls the number of *last* dictionary items
that will be read and written
(the items are ordered by keys, ascending) - default value is 3.
In order to read *all* items at once, the property
can also be set to "__all__" literal.
In order to read only a specific subset of keys, the property
can be set to a set of desired integers.
"""

# %%
# All items will be read.
db._subscripts[NameConfig._requests_field] = "__all__"

# %%
# 5 last items will be read.
db._subscripts[NameConfig._requests_field] = 5

# %%
# Items 1, 3, 5 and 7 will be read.
db._subscripts[NameConfig._requests_field] = {1, 3, 5, 7}

# %% [markdown]
"""
Last but not least, comes `rewrite_existing` boolean flag.
In order to understand it, let's explore `ContextDict` class more.

`ContextDict` provides dict-like access to its elements, however
by default not all of them might be loaded from the very beginning.
Usually, only the keys are loaded completely, while values loading is
controlled by `subscript` mentioned above.

Still, `ContextDict` allows accessing items that are not yet loaded
(they are loaded lazily), as well as deleting and overwriting them.
Once `ContextDict` is serialized, it always includes information about
all the added and removed elements.
As for the modified elements, that's where `rewrite_existing` flag
comes into play: if it is set to `True`, modifications are included,
otherwise they are discarded.

NB! Keeping track of the modified elements comes with a price of calculating
their hashes and comparing them, so in performance-critical environments
this feature probably might be avoided.
"""

# %%
# Any modifications done to the elements already present in storage
# will be preserved.
db.rewrite_existing = True

# %% [markdown]
"""
A few more words about the `labels`, `requests` and `responses` fields.
One and only one label, request and response is added on every dialog turn,
and they are numbered consecutively.

Framework ensures this ordering is preserved, each of them can be modified or
replaced with `None`, but never deleted or removed completely.
"""

# %%
if __name__ == "__main__":
    check_happy_path(pipeline, HAPPY_PATH)
    # This is a function for automatic
    # tutorial running (testing) with HAPPY_PATH

    # This runs tutorial in interactive mode if not in IPython env
    # and if `DISABLE_INTERACTIVE_MODE` is not set
    if is_interactive_mode():
        pipeline.run()  # This runs tutorial in interactive mode
