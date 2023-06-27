import pathlib
import typing as tp
from platform import system

from dff.utils.benchmark.context_storage import save_results_to_file, BenchmarkCase, DBFactory, BenchmarkConfig


# partial-specific logic
def get_cases(
    db_uris: tp.Dict[str, str],
    case_name_postfix: str = "",
    benchmark_config: BenchmarkConfig = BenchmarkConfig(),
    description: str = "",
):
    benchmark_cases = []
    for db, uri in db_uris.items():
        benchmark_cases.append(
            BenchmarkCase(
                name=db + "-dev" + case_name_postfix,
                db_factory=DBFactory(uri=uri, factory_module="dff.context_storages_old"),
                benchmark_config=benchmark_config,
                description=description,
            )
        )
        benchmark_cases.append(
            BenchmarkCase(
                name=db + "-partial" + case_name_postfix,
                db_factory=DBFactory(uri=uri),
                benchmark_config=benchmark_config,
                description=description,
            )
        )
    return benchmark_cases


def benchmark_all(
    file: tp.Union[str, pathlib.Path],
    name: str,
    description: str,
    db_uris: tp.Dict[str, str],
    case_name_postfix: str = "",
    benchmark_config: BenchmarkConfig = BenchmarkConfig(),
    exist_ok: bool = False,
):
    save_results_to_file(
        get_cases(
            db_uris,
            case_name_postfix,
            benchmark_config=benchmark_config,
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
    "Shelve": "shelve://dbs/shelve",
    "PostgreSQL": "postgresql+asyncpg://postgres:pass@localhost:5432/test",
    "MongoDB": "mongodb://admin:pass@localhost:27017/admin",
    "Redis": "redis://:pass@localhost:6379/0",
    "MySQL": "mysql+asyncmy://root:pass@localhost:3307/test",
    "SQLite": f"sqlite+aiosqlite:{sqlite_separator}{sqlite_file.absolute()}",
    # "YDB": "grpc://localhost:2136/local",
}

# benchmark
pathlib.Path("benchmarks").mkdir(exist_ok=True)

benchmark_all(
    "benchmarks/alexaprize1.json",
    "Alexaprize-like dialogue benchmarks",
    "Benchmark with dialogues similar to those from alexaprize.",
    db_uris=dbs,
    benchmark_config=BenchmarkConfig(
        from_dialog_len=1,
        to_dialog_len=50,
        message_dimensions=(3, 5, 6, 5, 3),
        misc_dimensions=(2, 4, 3, 8, 100),
    )
)

benchmark_all(
    "benchmarks/short_messages.json",
    "Short messages",
    "Benchmark with short messages, long dialog len.",
    db_uris=dbs,
    benchmark_config=BenchmarkConfig(
        from_dialog_len=500,
        to_dialog_len=550,
        message_dimensions=(2, 30),
        misc_dimensions=(0, 0),
    )
)

benchmark_all(
    "benchmarks/default.json",
    "Default",
    "Benchmark using default parameters.",
    db_uris=dbs,
)

benchmark_all(
    "benchmarks/alexaprize_longer.json",
    "Alexaprize-like dialogue benchmarks (longer)",
    "Benchmark with dialogues similar to those from alexaprize, but dialog len is increased.",
    db_uris=dbs,
    benchmark_config=BenchmarkConfig(
        from_dialog_len=500,
        to_dialog_len=550,
        message_dimensions=(3, 5, 6, 5, 3),
        misc_dimensions=(2, 4, 3, 8, 100),
    )
)

save_results_to_file(
    [
        *get_cases(
            db_uris=dbs,
            case_name_postfix="-long-dialog-len",
            benchmark_config=BenchmarkConfig(
                context_num=10,
                from_dialog_len=10000,
                to_dialog_len=10050,
            ),
            description="Benchmark with very long dialog len."
        ),
        *get_cases(
            db_uris=dbs,
            case_name_postfix="-long-message-len",
            benchmark_config=BenchmarkConfig(
                context_num=10,
                from_dialog_len=1,
                to_dialog_len=3,
                message_dimensions=(10000, 1),
            ),
            description="Benchmark with messages containing many keys."
        ),
        *get_cases(
            db_uris=dbs,
            case_name_postfix="-long-misc-len",
            benchmark_config=BenchmarkConfig(
                context_num=10,
                from_dialog_len=1,
                to_dialog_len=3,
                misc_dimensions=(10000, 1),
            ),
            description="Benchmark with misc containing many keys."
        ),
    ],
    file="benchmarks/extremes.json",
    name="Extreme",
    description="Set of benchmarks testing extreme cases."
)
