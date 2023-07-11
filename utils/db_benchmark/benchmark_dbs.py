"""
Benchmark DBs
-------------
This module contains config presets for benchmarks.
"""
import pathlib
import typing as tp
from platform import system

from dff.utils.benchmark.context_storage import save_results_to_file, BenchmarkCase, DBFactory, BenchmarkConfig


# partial-specific logic
def get_cases(
    db_uri: str,
    benchmark_configs: tp.Dict[str, BenchmarkConfig],
    description: str = "",
):
    benchmark_cases = []
    for config_name, config in benchmark_configs.items():
        benchmark_cases.append(
            BenchmarkCase(
                name=config_name + "-dev",
                db_factory=DBFactory(uri=db_uri, factory_module="dff.context_storages_old"),
                benchmark_config=config,
                description=description,
            )
        )
        benchmark_cases.append(
            BenchmarkCase(
                name=config_name + "-partial",
                db_factory=DBFactory(uri=db_uri),
                benchmark_config=config,
                description=description,
            )
        )
    return benchmark_cases


def benchmark_all(
    file: tp.Union[str, pathlib.Path],
    name: str,
    description: str,
    db_uri: str,
    benchmark_configs: tp.Dict[str, BenchmarkConfig],
    exist_ok: bool = False,
):
    save_results_to_file(
        get_cases(
            db_uri,
            benchmark_configs=benchmark_configs,
            description=description,
        ),
        file,
        name,
        description,
        exist_ok=exist_ok
    )


# create dir and files
pathlib.Path("dbs").mkdir(exist_ok=True)
sqlite_file = pathlib.Path("dbs/sqlite.db")
sqlite_file.touch(exist_ok=True)
sqlite_separator = "///" if system() == "Windows" else "////"

dbs = {
    # "JSON": "json://dbs/json.json",
    # "Pickle": "pickle://dbs/pickle.pkl",
    # "Shelve": "shelve://dbs/shelve",
    "PostgreSQL": "postgresql+asyncpg://postgres:pass@localhost:5432/test",
    # "MongoDB": "mongodb://admin:pass@localhost:27017/admin",
    # "Redis": "redis://:pass@localhost:6379/0",
    "MySQL": "mysql+asyncmy://root:pass@localhost:3307/test",
    "SQLite": f"sqlite+aiosqlite:{sqlite_separator}{sqlite_file.absolute()}",
    # "YDB": "grpc://localhost:2136/local",
}

# benchmark
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
            "large-misc-long-dialog": BenchmarkConfig(
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
