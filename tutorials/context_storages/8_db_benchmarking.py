# %% [markdown]
"""
# 8. Context storage benchmarking

This tutorial shows how to benchmark context storages.

For more info see [API reference](../apiref/dff.utils.benchmark.context_storage.rst).
"""

# %%
import pathlib
from platform import system
import tempfile

import dff.utils.benchmark.context_storage as benchmark

# %% [markdown]
"""
## Context storage setup
"""

# %%
# this cell is only required for pickle, shelve and sqlite databases
tutorial_dir = pathlib.Path(tempfile.mkdtemp())
db_path = tutorial_dir / "dbs"
db_path.mkdir()
sqlite_file = db_path / "sqlite.db"
sqlite_file.touch(exist_ok=True)
sqlite_separator = "///" if system() == "Windows" else "////"

# %%
storages = {
    "JSON": f"json://{db_path}/json.json",
    "Pickle": f"pickle://{db_path}/pickle.pkl",
    "Shelve": f"shelve://{db_path}/shelve",
    "PostgreSQL": "postgresql+asyncpg://postgres:pass@localhost:5432/test",
    "MongoDB": "mongodb://admin:pass@localhost:27017/admin",
    "Redis": "redis://:pass@localhost:6379/0",
    "MySQL": "mysql+asyncmy://root:pass@localhost:3307/test",
    "SQLite": f"sqlite+aiosqlite:{sqlite_separator}{sqlite_file.absolute()}",
    "YDB": "grpc://localhost:2136/local",
}

# %% [markdown]
"""
## Generating a report

The report will print a size of one context and stats for the context storage:
average write, read, update times.

Note: context storage passed into the `report` function will be cleared.

Setting `context_num` to 50 means that we'll run fifty cycles of writing and reading context.
This way we'll be able to get a more accurate average read/write time as well as
check if read/write times are dependent on the number of contexts in the storage.

You can also configure the `dialog_len`, `message_dimensions` and `misc_dimensions` parameters.
This allows you to set the context you want the benchmarks to run with.

For more info on each configuration parameter see [BenchmarkConfig](
../apiref/dff.utils.benchmark.context_storage.rst#dff.utils.benchmark.context_storage.BenchmarkConfig
).
"""

# %%
benchmark.report(
    storages,
    benchmark_config=benchmark.BenchmarkConfig(
        context_num=50,
        from_dialog_len=1,
        to_dialog_len=5,
        message_dimensions=(3, 10),
        misc_dimensions=(3, 10),
    ),
)

# %% [markdown]
"""
## Saving benchmark results to a file

Instead of printing the results into console, you can save them to a file.

For that there exist two functions:
[benchmark_all](
../apiref/dff.utils.benchmark.context_storage.rst#dff.utils.benchmark.context_storage.benchmark_all
)
and
[save_results_to_file](
../apiref/dff.utils.benchmark.context_storage.rst#dff.utils.benchmark.context_storage.save_results_to_file
).

The first one is a higher-level wrapper of the second one.

The files are saved according to this [schema](../../../utils/db_benchmark/benchmark_schema.json).

The schema can also be found on [github](
https://github.com/deeppavlov/dialog_flow_framework/blob/dev/utils/db_benchmark/benchmark_schema.json
).
"""

# %%
benchmark.benchmark_all(
    file=tutorial_dir / "results.json",
    name="Tutorial benchmark",
    description="Benchmark for tutorial",
    db_uris=storages,
    benchmark_config=benchmark.BenchmarkConfig(
        context_num=50,
        from_dialog_len=1,
        to_dialog_len=5,
        message_dimensions=(3, 10),
        misc_dimensions=(3, 10),
    ),
)

# %% [markdown]
"""
## Viewing benchmark results

Now that the results are saved to a file you can either view them manually or
use [our streamlit app](
../../../utils/db_benchmark/benchmark_streamlit.py
).

The app can also be found on [github](
https://github.com/deeppavlov/dialog_flow_framework/blob/dev/utils/db_benchmark/benchmark_streamlit.py
).
"""
