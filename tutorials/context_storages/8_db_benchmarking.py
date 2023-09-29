# %% [markdown]
"""
# 8. Context storage benchmarking

This tutorial shows how to benchmark context storages.

For more info see [API reference](%doclink(api,utils.db_benchmark.benchmark)).
"""

# %pip install dff[benchmark,json,pickle,postgresql,mongodb,redis,mysql,sqlite,ydb]

# %%
from pathlib import Path
from platform import system
import tempfile

import dff.utils.db_benchmark as benchmark

# %% [markdown]
"""
## Context storage setup
"""

# %%
# this cell is only required for pickle, shelve and sqlite databases
tutorial_dir = Path(tempfile.mkdtemp())
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
## Saving benchmark results to a file

Benchmark results are saved to files.

For that there exist two functions:
[benchmark_all](
%doclink(api,utils.db_benchmark.benchmark,benchmark_all)
)
and
[save_results_to_file](
%doclink(api,utils.db_benchmark.benchmark,save_results_to_file)
).

Note: context storages passed into these functions will be cleared.

### Configuration

The first one is a higher-level wrapper of the second one.
The first function accepts [BenchmarkCases](
%doclink(api,utils.db_benchmark.benchmark,BenchmarkCase)
) which configure databases that are being benchmark and configurations of the benchmarks.
The second function accepts only a single URI for the database and several benchmark configurations.
So, the second function is simpler to use, while the first function allows for more configuration
(e.g. having different databases benchmarked in a single file).

Both function use [BenchmarkConfig](
%doclink(api,utils.db_benchmark.benchmark,BenchmarkConfig)
) to configure benchmark behaviour.
`BenchmarkConfig` is only an interface for benchmark configurations.
Its most basic implementation is
[BasicBenchmarkConfig](
%doclink(api,utils.db_benchmark.basic_config,BasicBenchmarkConfig)
).

It has several parameters:

Setting `context_num` to 50 means that we'll run fifty cycles of writing and reading context.
This way we'll be able to get a more accurate average read/write time as well as
check if read/write times are dependent on the number of contexts in the storage.

You can also configure the `dialog_len`, `message_dimensions` and `misc_dimensions` parameters.
This allows you to set the contexts you want your database to be benchmarked with.

### File structure

The files are saved according to [the schema](
../_misc/benchmark_schema.json
).
"""

# %%
for db_name, db_uri in storages.items():
    benchmark.benchmark_all(
        file=tutorial_dir / f"{db_name}.json",
        name="Tutorial benchmark",
        description="Benchmark for tutorial",
        db_uri=db_uri,
        benchmark_configs={
            "simple_config": benchmark.BasicBenchmarkConfig(
                context_num=50,
                from_dialog_len=1,
                to_dialog_len=5,
                message_dimensions=(3, 10),
                misc_dimensions=(3, 10),
            ),
        },
    )

# %% [markdown]
"""
Running the cell above will create a file with benchmark results for every benchmarked DB:
"""

# %%
list(tutorial_dir.iterdir())

# %% [markdown]
"""
## Viewing benchmark results

Now that the results are saved to a file you can either view them using [report](
%doclink(api,utils.db_benchmark.report,report)
) function or [our streamlit app](
../_misc/benchmark_streamlit.py
).
"""

# %% [markdown]
"""
### Using the report function

The report function will print specified information from a given file.

By default it prints the name and average metrics for each case.
"""

# %%
benchmark.report(file=tutorial_dir / "Shelve.json", display={"name", "config", "metrics"})

# %% [markdown]
"""
### Using Streamlit app

To run the app, execute:

```
# download file
curl https://deeppavlov.github.io/dialog_flow_framework/_misc/benchmark_streamlit.py \
-o benchmark_streamlit.py
# install dependencies
pip install dff[benchmark]
# run
streamlit run benchmark_streamlit.py
```

You can upload files with benchmark results using the first tab of the app ("Benchmark sets"):

.. figure:: ../_static/images/benchmark_sets.png

The second tab ("View") lets you inspect individual benchmark results.
It also allows you to add a specific benchmark result
to the "Compare" tab via the button in the top-right corner.

.. figure:: ../_static/images/benchmark_view.png

In the "Compare" tab you can view main metrics (write, read, update, read+update)
of previously added benchmark results:

.. figure:: ../_static/images/benchmark_compare.png

"Mass compare" tab saves you the trouble of manually adding
to compare every benchmark result from a single file.

.. figure:: ../_static/images/benchmark_mass_compare.png
"""

# %% [markdown]
"""
## Additional information

### Configuration presets

The [dff.utils.db_benchmarks.basic_config](
%doclink(api,utils.db_benchmark.basic_config)
) module also includes a dictionary containing configuration presets.
Those cover various contexts and messages as well as some edge cases.

To use configuration presets, simply pass them to benchmark functions.
"""

# %%
print(benchmark.basic_configurations.keys())

# benchmark.benchmark_all(
#     ...,
#     benchmark_configs=benchmark.basic_configurations
# )

# %% [markdown]
"""
### Custom configuration

If the basic configuration is not enough for you, you can create your own.

To do so, inherit from the [dff.utils.db_benchmark.benchmark.BenchmarkConfig](
%doclink(api,utils.db_benchmark.benchmark,BenchmarkConfig)
) class. You need to define three methods:

- `get_context` -- method to get initial contexts.
- `info` -- method for getting display info representing the configuration.
- `context_updater` -- method for updating contexts.
"""
