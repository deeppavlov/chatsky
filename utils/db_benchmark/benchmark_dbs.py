"""
Benchmark DBs
-------------
This module contains config presets for benchmarks.
"""
import pathlib
from platform import system

from dff.utils.db_benchmark.benchmark import (
    BenchmarkConfig,
    benchmark_all,
)


# these files are required for file-based dbs
pathlib.Path("dbs").mkdir(exist_ok=True)
sqlite_file = pathlib.Path("dbs/sqlite.db")
sqlite_file.touch(exist_ok=True)
sqlite_separator = "///" if system() == "Windows" else "////"

dbs = {
    "JSON": "json://dbs/json.json",
    "Pickle": "pickle://dbs/pickle.pkl",
    "Shelve": "shelve://dbs/shelve",
    "PostgreSQL": "postgresql+asyncpg://postgres:pass@localhost:5432/test",
    "MongoDB": "mongodb://admin:pass@localhost:27017/admin",
    "Redis": "redis://:pass@localhost:6379/0",
    "MySQL": "mysql+asyncmy://root:pass@localhost:3307/test",
    "SQLite": f"sqlite+aiosqlite:{sqlite_separator}{sqlite_file.absolute()}",
    "YDB": "grpc://localhost:2136/local",
}

# benchmarks will be saved to this directory
benchmark_dir = pathlib.Path("benchmarks")

benchmark_dir.mkdir(exist_ok=True)


for db_name, db_uri in dbs.items():
    benchmark_all(
        benchmark_dir / f"{db_name}.json",
        db_name,
        description="Basic configs",
        db_uri=db_uri,
        benchmark_configs={
            "large-misc": BenchmarkConfig(
                from_dialog_len=1,
                to_dialog_len=50,
                message_dimensions=(3, 5, 6, 5, 3),
                misc_dimensions=(2, 4, 3, 8, 100),
            ),
            "short-messages": BenchmarkConfig(
                from_dialog_len=500,
                to_dialog_len=550,
                message_dimensions=(2, 30),
                misc_dimensions=(0, 0),
            ),
            "default": BenchmarkConfig(),
            "large-misc--long-dialog": BenchmarkConfig(
                from_dialog_len=500,
                to_dialog_len=550,
                message_dimensions=(3, 5, 6, 5, 3),
                misc_dimensions=(2, 4, 3, 8, 100),
            ),
            "very-long-dialog-len": BenchmarkConfig(
                context_num=10,
                from_dialog_len=10000,
                to_dialog_len=10050,
            ),
            "very-long-message-len": BenchmarkConfig(
                context_num=10,
                from_dialog_len=1,
                to_dialog_len=3,
                message_dimensions=(10000, 1),
            ),
            "very-long-misc-len": BenchmarkConfig(
                context_num=10,
                from_dialog_len=1,
                to_dialog_len=3,
                misc_dimensions=(10000, 1),
            ),
        },
    )
