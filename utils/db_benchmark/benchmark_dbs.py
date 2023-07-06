"""
Benchmark DBs
-------------
This module contains config presets for benchmarks.
"""
import pathlib
from platform import system

from dff.utils.benchmark.context_storage import (
    save_results_to_file,
    BenchmarkConfig,
    benchmark_all,
    BenchmarkCase,
    DBFactory,
)


# create dir and files
pathlib.Path("dbs").mkdir(exist_ok=True)
sqlite_file = pathlib.Path("dbs/sqlite.db")
sqlite_file.touch(exist_ok=True)
sqlite_separator = "///" if system() == "Windows" else "////"

dbs = {
    # "JSON": "json://dbs/json.json",
    # "Pickle": "pickle://dbs/pickle.pkl",
    "Shelve": "shelve://dbs/shelve",
    "PostgreSQL": "postgresql+asyncpg://postgres:pass@localhost:5432/test",
    "MongoDB": "mongodb://admin:pass@localhost:27017/admin",
    "Redis": "redis://:pass@localhost:6379/0",
    "MySQL": "mysql+asyncmy://root:pass@localhost:3307/test",
    "SQLite": f"sqlite+aiosqlite:{sqlite_separator}{sqlite_file.absolute()}",
    # "YDB": "grpc://localhost:2136/local",
}

# benchmark
benchmark_dir = pathlib.Path("benchmarks")

benchmark_dir.mkdir(exist_ok=True)

benchmark_all(
    benchmark_dir / "alexaprize.json",
    "Alexaprize-like dialogue benchmarks",
    "Benchmark with dialogues similar to those from alexaprize.",
    db_uris=dbs,
    benchmark_config=BenchmarkConfig(
        from_dialog_len=1,
        to_dialog_len=50,
        message_dimensions=(3, 5, 6, 5, 3),
        misc_dimensions=(2, 4, 3, 8, 100),
    ),
)

benchmark_all(
    benchmark_dir / "short_messages.json",
    "Short messages",
    "Benchmark with short messages, long dialog len.",
    db_uris=dbs,
    benchmark_config=BenchmarkConfig(
        from_dialog_len=500,
        to_dialog_len=550,
        message_dimensions=(2, 30),
        misc_dimensions=(0, 0),
    ),
)

benchmark_all(
    benchmark_dir / "default.json",
    "Default",
    "Benchmark using default parameters.",
    db_uris=dbs,
)

benchmark_all(
    benchmark_dir / "alexaprize_longer.json",
    "Alexaprize-like dialogue benchmarks (longer)",
    "Benchmark with dialogues similar to those from alexaprize, but dialog len is increased.",
    db_uris=dbs,
    benchmark_config=BenchmarkConfig(
        from_dialog_len=500,
        to_dialog_len=550,
        message_dimensions=(3, 5, 6, 5, 3),
        misc_dimensions=(2, 4, 3, 8, 100),
    ),
)

save_results_to_file(
    [
        *[
            BenchmarkCase(
                db_factory=DBFactory(uri=uri),
                name=name + "-long-dialog-len",
                benchmark_config=BenchmarkConfig(
                    context_num=10,
                    from_dialog_len=10000,
                    to_dialog_len=10050,
                ),
                description="Benchmark with very long dialog len.",
            )
            for name, uri in dbs.items()
        ],
        *[
            BenchmarkCase(
                db_factory=DBFactory(uri=uri),
                name=name + "-long-message-len",
                benchmark_config=BenchmarkConfig(
                    context_num=10,
                    from_dialog_len=1,
                    to_dialog_len=3,
                    message_dimensions=(10000, 1),
                ),
                description="Benchmark with messages containing many keys.",
            )
            for name, uri in dbs.items()
        ],
        *[
            BenchmarkCase(
                db_factory=DBFactory(uri=uri),
                name=name + "-long-misc-len",
                benchmark_config=BenchmarkConfig(
                    context_num=10,
                    from_dialog_len=1,
                    to_dialog_len=3,
                    misc_dimensions=(10000, 1),
                ),
                description="Benchmark with misc containing many keys.",
            )
            for name, uri in dbs.items()
        ],
    ],
    file=benchmark_dir / "extremes.json",
    name="Extreme",
    description="Set of benchmarks testing extreme cases.",
)
