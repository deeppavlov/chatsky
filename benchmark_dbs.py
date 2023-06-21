import pathlib
from platform import system
import typing as tp
from uuid import uuid4
import json
import importlib

from pympler import asizeof
from pydantic import BaseModel, Field

from dff.script import Context

import dff.utils.benchmark.context_storage as bm


# define benchmark classes and tools

class DBFactory(BaseModel):
    uri: str
    factory_module: str = "dff.context_storages"
    factory: str = "context_storage_factory"

    def db(self):
        module = importlib.import_module(self.factory_module)
        return getattr(module, self.factory)(self.uri)


class BenchmarkCase(BaseModel):
    name: str
    db_factory: DBFactory
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    description: str = ""
    context_num: int = 100
    from_dialog_len: int = 300
    to_dialog_len: int = 500
    step_dialog_len: int = 10
    message_lengths: tp.Tuple[int, ...] = (10, 10)
    misc_lengths: tp.Tuple[int, ...] = (10, 10)

    def get_context_updater(self):
        def _context_updater(context: Context):
            start_len = len(context.requests)
            if start_len + self.step_dialog_len < self.to_dialog_len:
                for i in range(start_len, start_len + self.step_dialog_len):
                    context.add_label((f"flow_{i}", f"node_{i}"))
                    context.add_request(bm.get_message(self.message_lengths))
                    context.add_response(bm.get_message(self.message_lengths))
                return context
            else:
                return None

        return _context_updater

    def sizes(self):
        return {
            "starting_context_size": asizeof.asizeof(
                bm.get_context(self.from_dialog_len, self.message_lengths, self.misc_lengths)
            ),
            "final_context_size": asizeof.asizeof(
                bm.get_context(self.to_dialog_len, self.message_lengths, self.misc_lengths)
            ),
            "misc_size": asizeof.asizeof(bm.get_dict(self.misc_lengths)),
            "message_size": asizeof.asizeof(bm.get_message(self.message_lengths)),
        }

    def run(self):
        try:
            write_times, read_times, update_times = bm.time_context_read_write(
                self.db_factory.db(),
                bm.get_context(self.from_dialog_len, self.message_lengths, self.misc_lengths),
                self.context_num,
                context_updater=self.get_context_updater()
            )
            return {
                "success": True,
                "result": {
                    "write_times": write_times,
                    "read_times": read_times,
                    "update_times": update_times,
                }
            }
        except Exception as e:
            return {
                "success": False,
                "result": getattr(e, "message", repr(e))
            }


def save_results_to_file(
    benchmark_cases: tp.List[BenchmarkCase],
    file: tp.Union[str, pathlib.Path],
    name: str,
    description: str,
):
    uuid = str(uuid4())
    result: tp.Dict[str, tp.Any] = {
        "name": name,
        "description": description,
        "uuid": uuid,
        "benchmarks": {},
    }
    for case in benchmark_cases:
        result["benchmarks"][case.uuid] = {**case.dict(), **case.sizes(), **case.run()}

    with open(file, "w", encoding="utf-8") as fd:
        json.dump(result, fd)


def get_cases(
    db_uris: tp.Dict[str, str],
    case_name_postfix: str = "",
    context_num: int = 100,
    from_dialog_len: int = 300,
    to_dialog_len: int = 500,
    step_dialog_len: int = 10,
    message_lengths: tp.Tuple[int, ...] = (10, 10),
    misc_lengths: tp.Tuple[int, ...] = (10, 10),
    description: str = "",
):
    benchmark_cases = []
    for db, uri in db_uris.items():
        benchmark_cases.append(
            BenchmarkCase(
                name=db + "-dev" + case_name_postfix,
                db_factory=DBFactory(uri=uri, factory_module="dff.context_storages_old"),
                context_num=context_num,
                from_dialog_len=from_dialog_len,
                to_dialog_len=to_dialog_len,
                step_dialog_len=step_dialog_len,
                message_lengths=message_lengths,
                misc_lengths=misc_lengths,
                description=description,
            )
        )
        benchmark_cases.append(
            BenchmarkCase(
                name=db + "-partial" + case_name_postfix,
                db_factory=DBFactory(uri=uri),
                context_num=context_num,
                from_dialog_len=from_dialog_len,
                to_dialog_len=to_dialog_len,
                step_dialog_len=step_dialog_len,
                message_lengths=message_lengths,
                misc_lengths=misc_lengths,
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
    context_num: int = 100,
    from_dialog_len: int = 300,
    to_dialog_len: int = 500,
    step_dialog_len: int = 10,
    message_lengths: tp.Tuple[int, ...] = (10, 10),
    misc_lengths: tp.Tuple[int, ...] = (10, 10),
):
    save_results_to_file(get_cases(
        db_uris,
        case_name_postfix,
        context_num,
        from_dialog_len,
        to_dialog_len,
        step_dialog_len,
        message_lengths,
        misc_lengths,
        description=description,
    ), file, name, description)


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
