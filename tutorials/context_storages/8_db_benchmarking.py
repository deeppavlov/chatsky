# %% [markdown]
"""
# 8. Context storage benchmarking

This tutorial shows how to benchmark context storages.
"""

# %%
import pathlib
from platform import system

from dff.context_storages import context_storage_factory

from dff.utils.benchmark.context_storage import report

# %% [markdown]
"""
## Context storage setup
"""

# %%
# this cell is only required for pickle, shelve and sqlite databases
pathlib.Path("dbs").mkdir(exist_ok=True)
sqlite_file = pathlib.Path("dbs/sqlite.db")
sqlite_file.touch(exist_ok=True)
sqlite_separator = "///" if system() == "Windows" else "////"

# %%
storages = list(
    map(
        context_storage_factory,
        [
            "json://dbs/json.json",
            "pickle://dbs/pickle.pkl",
            "shelve://dbs/shelve",
            "postgresql+asyncpg://postgres:pass@localhost:5432/test",
            "mongodb://admin:pass@localhost:27017/admin",
            "redis://:pass@localhost:6379/0",
            "mysql+asyncmy://root:pass@localhost:3307/test",
            f"sqlite+aiosqlite:{sqlite_separator}{sqlite_file.absolute()}",
            "grpc://localhost:2136/local",
        ],
    )
)

# %% [markdown]
"""
## Generating a report

The report will print a size of one context and stats for the context storage:
an average write time and an average write time.

Note: context storage passed into the `report` function will be cleared.

Setting `context_num` to 100 means that we'll run a hundred cycles of writing and reading context.
This way we'll be able to get a more accurate average read/write time as well as
check if read/write times are dependent on the number of contexts in the storage.

You can also set the `dialog_len` and `misc_len` parameters. Those affect the size of a context.
An approximate formula is `size=1000 * dialog_len + 100 * misc_len bytes` although the report
automatically calculates the size of a context.

Here we set `dialog_len` to 1 and `misc_len` to 0 (by default) in order for reports to
generate faster.
"""

# %%
report(context_storage_factory("json://dbs/json.json"), context_num=100, dialog_len=1)

# %% [markdown]
"""
You can pass multiple context storages to get average read/write times for each
as well as a comparison of all the passed storages (in the form of ordered lists).
"""

# %%
report(*storages, context_num=100, dialog_len=1)

# %% [markdown]
"""
You can also generate a pdf report which additionally includes
plots of write and read times for each storage.

Generating pdf reports requires the `matplotlib` package.
"""

# %%
report(*storages, context_num=100, dialog_len=1, pdf="report.pdf")
