"""
Benchmark
---------
This module contains functions used to benchmark context storages.

## Basic usage

```
from dff.utils.benchmark.context_storage import report
from dff.context_storages import context_storage_factory

storage = context_storage_factory("postgresql+asyncpg://postgres:pass@localhost:5432/test", table_name="benchmark")

report(storage)
```
"""
from uuid import uuid4
from time import perf_counter

from pympler import asizeof
from tqdm.auto import tqdm

from dff.context_storages import DBContextStorage
from dff.script import Context, Message


def get_context_size(context: Context):
    """Return size of a provided context."""
    return asizeof.asizeof(context)


def get_context(dialog_len: int, misc_len: int):
    """
    Return a context with a given number of dialog turns and a given length of misc field.

    Misc field is needed in case context storage reads only the most recent requests/responses.

    Context size is approximately 1000 * dialog_len + 100 * misc_len bytes if dialog_len and misc_len > 100.
    """
    return Context(
        labels={i: (f"flow_{i}", f"node_{i}") for i in range(dialog_len)},
        requests={i: Message(text=f"request_{i}") for i in range(dialog_len)},
        responses={i: Message(text=f"response_{i}") for i in range(dialog_len)},
        misc={str(i): i for i in range(misc_len)},
    )


def time_context_read_write(context_storage: DBContextStorage, context: Context, context_num: int):
    """
    Generate `context_num` ids and for each write into `context_storage` value of `context` under generated id,
    after that read the value stored in `context_storage` under generated id and compare it to `context`.

    Keep track of the time it takes to write and read context to/from the context storage.

    This function clear context storage before and after execution.

    :param context_storage: Context storage to benchmark.
    :param context: An instance of context which will be repeatedly written into context storage.
    :param context_num: A number of times the context will be written and checked.
    :return: Two lists: first one contains individual write times, second one contains individual read times.
    :raises RuntimeError: If context written into context storage does not match read context.
    """
    context_storage.clear()

    write_times: list[float] = []
    read_times: list[float] = []
    for _ in tqdm(range(context_num), desc="Benchmarking context storage"):
        ctx_id = uuid4()

        # write operation benchmark
        write_start = perf_counter()
        context_storage[ctx_id] = context
        write_times.append(perf_counter() - write_start)

        # read operation benchmark
        read_start = perf_counter()
        actual_context = context_storage[ctx_id]
        read_times.append(perf_counter() - read_start)

        # check returned context
        if actual_context != context:
            raise RuntimeError(f"True context:\n{context}\nActual context:\n{actual_context}")

    context_storage.clear()
    return write_times, read_times


def report(
        context_storage: DBContextStorage,
        context_num: int = 1000,
        dialog_len: int = 10000,
        misc_len: int = 0,
):
    """
    Benchmark context storage and generate a report.

    :param context_storage: Context storage to benchmark.
    :param context_num: Number of times a single context should be written to/read from context storage.
    :param dialog_len:
        A number of turns inside a single context. The context will contain simple text requests/responses.
    :param misc_len:
        Number of items in the misc field.
        Use this parameter if context storage only has access to the most recent requests/responses.
    """
    context = get_context(dialog_len, misc_len)
    context_size = get_context_size(context)

    benchmark_stats = f"""Number of contexts: {context_num}
Dialog len: {dialog_len}
Misc len: {misc_len}
Size of one context: {context_size} ({tqdm.format_sizeof(context_size, divisor=1024)})"""

    print(f"""Starting benchmarking with following parameters:
{benchmark_stats}""")

    write, read = time_context_read_write(context_storage, context, context_num)
    print(f"""--------------------------------------------------
DB benchmark
--------------------------------------------------
{benchmark_stats}
--------------------------------------------------
Result
--------------------------------------------------
Average write time for one context: {sum(write) / len(write)} s
Average read time for one context: {sum(read) / len(read)} s""")
