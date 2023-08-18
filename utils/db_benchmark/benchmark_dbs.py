"""
Benchmark DBs
-------------
This module contains config presets for benchmarks.
"""
from pathlib import Path
from platform import system

from dff.utils.db_benchmark import benchmark_all, basic_configurations


# these files are required for file-based dbs
Path("dbs").mkdir(exist_ok=True)
sqlite_file = Path("dbs/sqlite.db")
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
benchmark_dir = Path("benchmarks")

benchmark_dir.mkdir(exist_ok=True)


for db_name, db_uri in dbs.items():
    benchmark_all(
        benchmark_dir / f"{db_name}.json",
        db_name,
        description="Basic configs",
        db_uri=db_uri,
        benchmark_configs=basic_configurations,
    )
