import pathlib
from platform import system

from dff.utils.benchmark.context_storage import benchmark_all, save_results_to_file, get_cases


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
    "benchmarks/alexaprize.json",
    "Alexaprize-like dialogue benchmarks",
    "Benchmark with dialogues similar to those from alexaprize.",
    db_uris=dbs,
    from_dialog_len=1,
    to_dialog_len=50,
    message_lengths=(3, 5, 6, 5, 3),
    misc_lengths=(2, 4, 3, 8, 100),
)

benchmark_all(
    "benchmarks/short_messages.json",
    "Short messages",
    "Benchmark with short messages, long dialog len.",
    db_uris=dbs,
    from_dialog_len=100,
    to_dialog_len=1001,
    step_dialog_len=100,
    message_lengths=(2, 30),
    misc_lengths=(0, 0),
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
    from_dialog_len=100,
    to_dialog_len=1001,
    step_dialog_len=100,
    message_lengths=(3, 5, 6, 5, 3),
    misc_lengths=(2, 4, 3, 8, 100),
)

save_results_to_file(
    [
        *get_cases(
            db_uris=dbs,
            case_name_postfix="-long-dialog-len",
            from_dialog_len=10000,
            to_dialog_len=11001,
            step_dialog_len=100,
            description="Benchmark with very long dialog len."
        ),
        *get_cases(
            db_uris=dbs,
            case_name_postfix="-long-message-len",
            from_dialog_len=1,
            to_dialog_len=2,
            message_lengths=(10000, 1),
            description="Benchmark with messages containing many keys."
        ),
        *get_cases(
            db_uris=dbs,
            case_name_postfix="-long-misc-len",
            from_dialog_len=1,
            to_dialog_len=2,
            misc_lengths=(10000, 1),
            description="Benchmark with misc containing many keys."
        ),
    ],
    file="benchmarks/extremes.json",
    name="Extreme",
    description="Set of benchmarks testing extreme cases."
)
