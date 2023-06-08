"""
Context storage benchmarking
----------------------------
This module contains functions for context storages benchmarking.

Basic usage::


    from dff.utils.benchmark.context_storage import report
    from dff.context_storages import context_storage_factory

    storage = context_storage_factory("postgresql+asyncpg://postgres:pass@localhost:5432/test", table_name="benchmark")

    report(storage)

"""
from uuid import uuid4
from time import perf_counter
import typing as tp

from pympler import asizeof
from tqdm.auto import tqdm

try:
    import matplotlib
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = None

try:
    import pandas
except ImportError:
    pandas = None

try:
    import polars
except ImportError:
    polars = None

from dff.context_storages import DBContextStorage
from dff.script import Context, Message


def get_context_size(context: Context) -> int:
    """Return size of a provided context."""
    return asizeof.asizeof(context)


def get_context(dialog_len: int, misc_len: int) -> Context:
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


@tp.overload
def time_context_read_write(
        context_storage: DBContextStorage,
        context: Context,
        context_num: int,
        as_dataframe: None = None,
) -> tp.Tuple[tp.List[float], tp.List[float]]:
    ...


@tp.overload
def time_context_read_write(
        context_storage: DBContextStorage,
        context: Context,
        context_num: int,
        as_dataframe: tp.Literal["pandas"],
) -> "pandas.DataFrame":
    ...


@tp.overload
def time_context_read_write(
        context_storage: DBContextStorage,
        context: Context,
        context_num: int,
        as_dataframe: tp.Literal["polars"],
) -> "polars.DataFrame":
    ...


def time_context_read_write(
        context_storage: DBContextStorage,
        context: Context,
        context_num: int,
        as_dataframe: tp.Optional[tp.Literal["pandas", "polars"]] = None,
) -> tp.Union[
    tp.Tuple[tp.List[float], tp.List[float]],
    "pandas.DataFrame",
    "polars.DataFrame",
]:
    """
    Generate `context_num` ids and for each write into `context_storage` value of `context` under generated id,
    after that read the value stored in `context_storage` under generated id and compare it to `context`.

    Keep track of the time it takes to write and read context to/from the context storage.

    This function clear context storage before and after execution.

    :param context_storage: Context storage to benchmark.
    :param context: An instance of context which will be repeatedly written into context storage.
    :param context_num: A number of times the context will be written and checked.
    :param as_dataframe:
        If the function should return the results as a pandas or a polars DataFrame.
        If set to None, does not return a Dataframe.
        Defaults to None.
    :return:
        Depends on `as_dataframe` parameter.
        1. By default, it is set to None in which case it returns:
            two lists: first one contains individual write times, second one contains individual read times.
        2. If set to "pandas":
            A pandas DataFrame with two columns: "write" and "read" which contain corresponding data series.
        3. If set to "polars":
            A polars DataFrame with the same columns as in a pandas DataFrame.
    :raises RuntimeError: If context written into context storage does not match read context.
    """
    context_storage.clear()

    write_times: tp.List[float] = []
    read_times: tp.List[float] = []
    for _ in tqdm(range(context_num), desc=f"Benchmarking context storage:{context_storage.full_path}"):
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

    if as_dataframe is None:
        return write_times, read_times
    elif as_dataframe == "pandas":
        if pandas is None:
            raise RuntimeError("Install `pandas` in order to get benchmark results as a pandas DataFrame.")
        return pandas.DataFrame(data={
            "write": write_times,
            "read": read_times
        })
    elif as_dataframe == "polars":
        if polars is None:
            raise RuntimeError("Install `polars` in order to get benchmark results as a polars DataFrame.")
        return polars.DataFrame({
            "write": write_times,
            "read": read_times
        })


def report(
        *context_storages: DBContextStorage,
        context_num: int = 1000,
        dialog_len: int = 10000,
        misc_len: int = 0,
        pdf: tp.Optional[str] = None,
):
    """
    Benchmark context storage(s) and generate a report.

    :param context_storages: Context storages to benchmark.
    :param context_num: Number of times a single context should be written to/read from context storage.
    :param dialog_len:
        A number of turns inside a single context. The context will contain simple text requests/responses.
    :param misc_len:
        Number of items in the misc field.
        Use this parameter if context storage only has access to the most recent requests/responses.
    :param pdf:
        A pdf file name to save report to.
        Defaults to None.
        If set to None, prints the result to stdout instead of creating a pdf file.
    """
    context = get_context(dialog_len, misc_len)
    context_size = get_context_size(context)

    benchmark_config = f"Number of contexts: {context_num}\n" \
                      f"Dialog len: {dialog_len}\n" \
                      f"Misc len: {misc_len}\n" \
                      f"Size of one context: {context_size} ({tqdm.format_sizeof(context_size, divisor=1024)})"

    print(f"Starting benchmarking with following parameters:\n{benchmark_config}")

    benchmarking_results: tp.Dict[str, tp.Union[
        tp.Tuple[tp.List[float], tp.List[float]],
        str
    ]] = {}

    for context_storage in context_storages:
        try:
            write, read = time_context_read_write(context_storage, context, context_num)

            benchmarking_results[context_storage.full_path] = write, read
        except Exception as e:
            benchmarking_results[context_storage.full_path] = getattr(e, 'message', repr(e))

    # define functions for displaying results
    line_separator = "-" * 80

    pretty_config = f"{line_separator}\nDB benchmark\n{line_separator}\n{benchmark_config}\n{line_separator}"

    def pretty_benchmark_result(storage_name, benchmarking_result) -> str:
        result = f"{storage_name}\n{line_separator}\n"
        if not isinstance(benchmarking_result, str):
            write, read = benchmarking_result
            result += f"Average write time: {sum(write) / len(write)} s\n" \
                      f"Average read time: {sum(read) / len(read)} s\n{line_separator}"
        else:
            result += f"{benchmarking_result}\n{line_separator}"
        return result

    def get_scores_and_leaderboard(
            sort_by: tp.Literal["Write", "Read"]
    ) -> tp.Tuple[
        tp.List[tp.Tuple[str, tp.Optional[float]]],
        str
    ]:
        benchmark_index = 0 if sort_by == 'Write' else 1

        scores = sorted(
            [
                (storage_name, sum(result[benchmark_index]) / len(result[benchmark_index]))
                for storage_name, result in benchmarking_results.items()
                if not isinstance(result, str)
            ],
            key=lambda benchmark: benchmark[1]  # sort in ascending order
        )
        scores += [
            (storage_name, None)
            for storage_name, result in benchmarking_results.items()
            if isinstance(result, str)
        ]
        leaderboard = f"{sort_by} time leaderboard\n{line_separator}\n" + "\n".join(
            [f"{result}{' s' if result is not None else ''}: {storage_name}" for storage_name, result in scores]
        ) + "\n" + line_separator

        return scores, leaderboard

    _, write_leaderboard = get_scores_and_leaderboard("Write")
    _, read_leaderboard = get_scores_and_leaderboard("Read")

    if pdf is None:
        result = pretty_config

        for storage_name, benchmarking_result in benchmarking_results.items():
            result += f"\n{pretty_benchmark_result(storage_name, benchmarking_result)}"

        if len(context_storages) > 1:
            result += f"\n{write_leaderboard}\n{read_leaderboard}"

        print(result)
    else:
        if matplotlib is None:
            raise RuntimeError("`matplotlib` is required to generate pdf reports.")

        figure_size = (11, 8)

        def text_page(text, *, x=0.5, y=0.5, size=18, ha="center", family="monospace", **kwargs):
            page = plt.figure(figsize=figure_size)
            page.clf()
            page.text(x, y, text, transform=page.transFigure, size=size, ha=ha, family=family, **kwargs)

        def scatter_page(storage_name, write, read):
            plt.figure(figsize=figure_size)
            plt.scatter(range(len(write)), write, label="write times")
            plt.scatter(range(len(read)), read, label="read times")
            plt.legend(loc='best')
            plt.grid(True)
            plt.title(storage_name)

        with PdfPages(pdf) as mpl_pdf:
            text_page(pretty_config, size=24)
            mpl_pdf.savefig()
            plt.close()

            if len(context_storages) > 1:
                text_page(write_leaderboard, x=0.05, size=14, ha="left")
                mpl_pdf.savefig()
                plt.close()
                text_page(read_leaderboard, x=0.05, size=14, ha="left")
                mpl_pdf.savefig()
                plt.close()

            for storage_name, benchmarking_result in benchmarking_results.items():
                txt = pretty_benchmark_result(storage_name, benchmarking_result)

                if not isinstance(benchmarking_result, str):
                    write, read = benchmarking_result

                    text_page(txt)
                    mpl_pdf.savefig()
                    plt.close()

                    scatter_page(storage_name, write, read)
                    mpl_pdf.savefig()
                    plt.close()
                else:
                    text_page(txt)
                    mpl_pdf.savefig()
                    plt.close()
