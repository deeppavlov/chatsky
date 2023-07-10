"""
Context storage benchmarking
----------------------------
This module contains functions for context storages benchmarking.

The basic function is :py:func:`~.time_context_read_write` but it has a low level interface.

Higher level wrappers of the function provided by this module are:

- :py:func:`~.save_results_to_file` and :py:func:`~.benchmark_all` are used to save benchmark results to a file.
- :py:func:`~.report` is used to print results to stdout.

Wrappers use :py:class:`~.BenchmarkConfig` to configure benchmarks.
"""
from uuid import uuid4
import pathlib
from time import perf_counter
import typing as tp
from copy import deepcopy
import json
import importlib
from statistics import mean

from pydantic import BaseModel, Field
from pympler import asizeof
from tqdm.auto import tqdm
from humanize import naturalsize

from dff.context_storages import DBContextStorage
from dff.script import Context, Message


def get_dict(dimensions: tp.Tuple[int, ...]):
    """
    Return misc dictionary build in `dimensions` dimensions.

    :param dimensions:
        Dimensions of the dictionary.
        Each element of the dimensions tuple is the number of keys on the corresponding level of the dictionary.
        The last element of the dimensions tuple is the length of the string values of the dict.

        e.g. dimensions=(1, 2) returns a dictionary with 1 key that points to a string of len 2.
        whereas dimensions=(1, 2, 3) returns a dictionary with 1 key that points to a dictionary
        with 2 keys each of which points to a string of len 3.

        So, the len of dimensions is the depth of the dictionary, while its values are
        the width of the dictionary at each level.
    """

    def _get_dict(dimensions: tp.Tuple[int, ...]):
        if len(dimensions) < 2:
            return "." * dimensions[0]
        return {i: _get_dict(dimensions[1:]) for i in range(dimensions[0])}

    if len(dimensions) > 1:
        return _get_dict(dimensions)
    elif len(dimensions) == 1:
        return _get_dict((dimensions[0], 0))
    else:
        return _get_dict((0, 0))


def get_message(message_dimensions: tp.Tuple[int, ...]):
    """
    Return message with a non-empty misc field.

    :param message_dimensions: Dimensions of the misc field of the message. See :py:func:`~.get_dict`.
    """
    return Message(misc=get_dict(message_dimensions))


def get_context(
    dialog_len: int,
    message_dimensions: tp.Tuple[int, ...],
    misc_dimensions: tp.Tuple[int, ...],
) -> Context:
    """
    Return context with a non-empty misc, labels, requests, responses fields.

    :param dialog_len: Number of labels, requests and responses.
    :param message_dimensions:
        A parameter used to generate messages for requests and responses. See :py:func:`~.get_message`.
    :param misc_dimensions:
        A parameter used to generate misc field. See :py:func:`~.get_dict`.
    """
    return Context(
        labels={i: (f"flow_{i}", f"node_{i}") for i in range(dialog_len)},
        requests={i: get_message(message_dimensions) for i in range(dialog_len)},
        responses={i: get_message(message_dimensions) for i in range(dialog_len)},
        misc=get_dict(misc_dimensions),
    )


def time_context_read_write(
    context_storage: DBContextStorage,
    context: Context,
    context_num: int,
    context_updater=None,
) -> tp.Tuple[tp.List[float], tp.List[tp.Dict[int, float]], tp.List[tp.Dict[int, float]]]:
    """
    Benchmark "context_storage" by writing and reading `context` into it / from it `context_num` times.
    If context_updater is not None it is used to update `context` and use it to benchmark updating contexts
    (as well as reading updated contexts).

    This function clears "context_storage" before and after execution.

    :param context_storage: Context storage to benchmark.
    :param context: An instance of context which will be repeatedly written into context storage.
    :param context_num: A number of times the context will be written and read.
    :param context_updater:
        None or a function.
        If not None, function should accept :py:class:`~.Context` and return an updated :py:class:`~.Context`.
        The updated context can be either the same object (at the same pointer) or a different object (e.g. copied).
        The updated context should have a higher dialog length than the received context
        (to emulate context updating during dialog).
        The function should return `None` to stop updating contexts.
        For an example of such function, see :py:meth:`~.BenchmarkConfig.get_context_updater`.

        To avoid keeping many contexts in memory,
        this function will be called with every argument `context_num` times (for each cycle), so it should
        return the same updated context for the same context and shouldn't take a long time to update a context.
    :return:
        A tuple of 3 elements.

        The first element -- a list of write times. Its length is equal to `context_num`.

        The second element -- a list of dictionaries with read times.
        Each dictionary maps from int to float. The key in the mapping is the `dialog_len` of the context and the
        values are the read times for the corresponding `dialog_len`.
        If `context_updater` is None, all dictionaries will have only one key -- dialog length of `context`.
        Otherwise, the dictionaries will also have a key for each updated context.

        The third element -- a list of dictionaries with update times.
        Structurally the same as the second element, but none of the elements here have a key for
        dialog_len of the `context`.
        So if `context_updater` is None, all dictionaries will be empty.
    """
    context_storage.clear()

    write_times: tp.List[float] = []
    read_times: tp.List[tp.Dict[int, float]] = []
    update_times: tp.List[tp.Dict[int, float]] = []

    for _ in tqdm(range(context_num), desc=f"Benchmarking context storage:{context_storage.full_path}", leave=False):
        tmp_context = deepcopy(context)

        ctx_id = uuid4()

        # write operation benchmark
        write_start = perf_counter()
        context_storage[ctx_id] = tmp_context
        write_times.append(perf_counter() - write_start)

        read_times.append({})
        update_times.append({})

        # read operation benchmark
        read_start = perf_counter()
        _ = context_storage[ctx_id]
        read_time = perf_counter() - read_start
        read_times[-1][len(tmp_context.labels)] = read_time

        if context_updater is not None:
            tmp_context = context_updater(tmp_context)

            while tmp_context is not None:
                update_start = perf_counter()
                context_storage[ctx_id] = tmp_context
                update_time = perf_counter() - update_start
                update_times[-1][len(tmp_context.labels)] = update_time

                read_start = perf_counter()
                _ = context_storage[ctx_id]
                read_time = perf_counter() - read_start
                read_times[-1][len(tmp_context.labels)] = read_time

                tmp_context = context_updater(tmp_context)

        context_storage.clear()
    return write_times, read_times, update_times


class DBFactory(BaseModel):
    """
    A class for storing information about context storage to benchmark.
    Also used to create a context storage from the configuration.
    """

    uri: str
    """URI of the context storage."""
    factory_module: str = "dff.context_storages"
    """A module containing `factory`."""
    factory: str = "context_storage_factory"
    """Name of the context storage factory. (function that creates context storages from URIs)"""

    def db(self):
        """
        Create a context storage using `factory` from `uri`.
        """
        module = importlib.import_module(self.factory_module)
        return getattr(module, self.factory)(self.uri)


class BenchmarkConfig(BaseModel):
    """
    Configuration for a benchmark. Sets dialog len, misc sizes, number of benchmarks.
    """

    context_num: int = 30
    """
    Number of times the contexts will be benchmarked.
    Increasing this number decreases standard error of the mean for benchmarked data.
    """
    from_dialog_len: int = 300
    """Starting dialog len of a context."""
    to_dialog_len: int = 311
    """
    Final dialog len of a context.
    :py:meth:`~.BenchmarkConfig.get_context_updater` will return contexts
    until their dialog len is less then `to_dialog_len`.
    """
    step_dialog_len: int = 1
    """
    Increment step for dialog len.
    :py:meth:`~.BenchmarkConfig.get_context_updater` will return contexts
    increasing dialog len by `step_dialog_len`.
    """
    message_dimensions: tp.Tuple[int, ...] = (10, 10)
    """
    Dimensions of misc dictionaries inside messages.
    See :py:func:`~.get_message`.
    """
    misc_dimensions: tp.Tuple[int, ...] = (10, 10)
    """
    Dimensions of misc dictionary.
    See :py:func:`~.get_dict`.
    """

    class Config:
        allow_mutation = False

    def get_context(self):
        """
        Return context with `from_dialog_len`, `message_dimensions`, `misc_dimensions`.

        Wraps :py:func:`~.get_context`.
        """
        return get_context(self.from_dialog_len, self.message_dimensions, self.misc_dimensions)

    def sizes(self):
        """
        Return sizes of objects defined by this config.

        :return:
            A dictionary with 4 elements:
                - "starting_context_size" -- size of a context with `from_dialog_len`.
                - "final_context_size" -- size of a context with `to_dialog_len`.
                  A context of this size will never actually be benchmarked.
                - "misc_size" -- size of a misc field of a context.
                - "message_size" -- size of a misc field of a message.
        """
        return {
            "starting_context_size": asizeof.asizeof(self.get_context()),
            "final_context_size": asizeof.asizeof(
                get_context(self.to_dialog_len, self.message_dimensions, self.misc_dimensions)
            ),
            "misc_size": asizeof.asizeof(get_dict(self.misc_dimensions)),
            "message_size": asizeof.asizeof(get_message(self.message_dimensions)),
        }

    def get_context_updater(self):
        """
        Return context updater function based on configuration.

        :return:
            A function that accepts a context, modifies it and returns it.
            The updated context has `step_dialog_len` more labels, requests and responses,
            unless such dialog len would be equal to `to_dialog_len` or exceed than it,
            in which case None is returned.
        """

        def _context_updater(context: Context):
            start_len = len(context.labels)
            if start_len + self.step_dialog_len < self.to_dialog_len:
                for i in range(start_len, start_len + self.step_dialog_len):
                    context.add_label((f"flow_{i}", f"node_{i}"))
                    context.add_request(get_message(self.message_dimensions))
                    context.add_response(get_message(self.message_dimensions))
                return context
            else:
                return None

        return _context_updater


class BenchmarkCase(BaseModel):
    """
    This class represents a benchmark case and includes
    information about it, its configuration and configuration of a context storage to benchmark.
    """

    name: str
    """Name of a benchmark case."""
    db_factory: DBFactory
    """DBFactory that specifies context storage to benchmark."""
    benchmark_config: BenchmarkConfig = BenchmarkConfig()
    """Benchmark configuration."""
    uuid: str = Field(default_factory=lambda: str(uuid4()))
    """Unique id of the case. Defaults to a random uuid."""
    description: str = ""
    """Description of the case. Defaults to an empty string."""

    @staticmethod
    def set_average_results(benchmark):
        """
        Modify `benchmark` dictionary to include averaged benchmark results.

        Add field "average_results" to the benchmark that contains the following fields:

            - average_write_time
            - average_read_time
            - average_update_time
            - read_times_grouped_by_context_num -- a list of read times.
              Each element is the average of read times with the same context_num.
            - read_times_grouped_by_dialog_len -- a dictionary of read times.
              Its values are the averages of read times with the same dialog_len,
              its keys are dialog_len values.
            - update_times_grouped_by_context_num
            - update_times_grouped_by_dialog_len
            - pretty_write -- average write time with only 3 significant digits.
            - pretty_read
            - pretty_update
            - pretty_read+update -- sum of average read and update times with only 3 significant digits.

        :param benchmark:
            A dictionary returned by `BenchmarkCase._run`.
            Should include a "success" and "result" fields.
            "success" field should be true.
            "result" field should be a dictionary with the values returned by
            :py:func:`~.time_context_read_write` and keys
            "write_times", "read_times" and "update_times".
        :return: None
        """
        if not benchmark["success"] or isinstance(benchmark["result"], str):
            return

        def get_complex_stats(results):
            if len(results) == 0 or len(results[0]) == 0:
                return [], {}, None

            average_grouped_by_context_num = [mean(times.values()) for times in results]
            average_grouped_by_dialog_len = {key: mean([times[key] for times in results]) for key in results[0].keys()}
            average = float(mean(average_grouped_by_context_num))
            return average_grouped_by_context_num, average_grouped_by_dialog_len, average

        read_stats = get_complex_stats(benchmark["result"]["read_times"])
        update_stats = get_complex_stats(benchmark["result"]["update_times"])

        result = {
            "average_write_time": mean(benchmark["result"]["write_times"]),
            "average_read_time": read_stats[2],
            "average_update_time": update_stats[2],
            "read_times_grouped_by_context_num": read_stats[0],
            "read_times_grouped_by_dialog_len": read_stats[1],
            "update_times_grouped_by_context_num": update_stats[0],
            "update_times_grouped_by_dialog_len": update_stats[1],
        }
        result["pretty_write"] = (
            float(f'{result["average_write_time"]:.3}') if result["average_write_time"] is not None else None
        )
        result["pretty_read"] = (
            float(f'{result["average_read_time"]:.3}') if result["average_read_time"] is not None else None
        )
        result["pretty_update"] = (
            float(f'{result["average_update_time"]:.3}') if result["average_update_time"] is not None else None
        )
        result["pretty_read+update"] = (
            float(f'{result["average_read_time"] + result["average_update_time"]:.3}')
            if result["average_read_time"] is not None and result["average_update_time"] is not None
            else None
        )

        benchmark["average_results"] = result

    def _run(self):
        try:
            write_times, read_times, update_times = time_context_read_write(
                self.db_factory.db(),
                self.benchmark_config.get_context(),
                self.benchmark_config.context_num,
                context_updater=self.benchmark_config.get_context_updater(),
            )
            return {
                "success": True,
                "result": {
                    "write_times": write_times,
                    "read_times": read_times,
                    "update_times": update_times,
                },
            }
        except Exception as e:
            exception_message = getattr(e, "message", repr(e))
            print(exception_message)
            return {
                "success": False,
                "result": exception_message,
            }

    def run(self):
        """
        Run benchmark, return results.

        :return:
            A dictionary with 3 keys: "success", "result", "average_results".

            Success is a bool value. It is false if an exception was raised during benchmarking.

            Result is either an exception message or a dictionary with 3 keys
            ("write_times", "read_times", "update_times").
            Values of those fields are the values returned by :py:func:`~.time_context_read_write`.

            Average results field is as described in :py:meth:`~.BenchmarkCase.set_average_results`.
        """
        benchmark = self._run()
        BenchmarkCase.set_average_results(benchmark)
        return benchmark


def save_results_to_file(
    benchmark_cases: tp.List[BenchmarkCase],
    file: tp.Union[str, pathlib.Path],
    name: str,
    description: str,
    exist_ok: bool = False,
):
    """
    Benchmark all `benchmark_cases` and save results to a file.

    Result are saved in json format with this schema (click to expand):

    .. collapse:: utils/db_benchmark/benchmark_schema.json

        .. literalinclude:: ../../../utils/db_benchmark/benchmark_schema.json


    Files created by this function cen be viewed with the streamlit app located in the same directory:

    .. collapse:: utils/db_benchmark/benchmark_streamlit.py

        .. literalinclude:: ../../../utils/db_benchmark/benchmark_streamlit.py

    :param benchmark_cases: A list of benchmark cases that specify benchmarks.
    :param file: File to save results to.
    :param name: Name of the benchmark set.
    :param description: Description of the benchmark set.
    :param exist_ok: Whether to continue if the file already exists.
    """
    with open(file, "w" if exist_ok else "x", encoding="utf-8") as fd:
        uuid = str(uuid4())
        result: tp.Dict[str, tp.Any] = {
            "name": name,
            "description": description,
            "uuid": uuid,
            "benchmarks": [],
        }
        cases = tqdm(benchmark_cases, leave=False)
        for case in cases:
            cases.set_description(f"Benchmarking: {case.name}")
            result["benchmarks"].append({**case.dict(), "sizes": case.benchmark_config.sizes(), **case.run()})

        json.dump(result, fd)


def benchmark_all(
    file: tp.Union[str, pathlib.Path],
    name: str,
    description: str,
    db_uri: str,
    benchmark_configs: tp.Dict[str, BenchmarkConfig],
    exist_ok: bool = False,
):
    """
    A wrapper for :py:func:`~.save_results_to_file`.

    Generates `benchmark_cases` from `db_uri` and `benchmark_configs`:
    `db_uri` is used to initialize :py:class:`~.DBFactory` instance
    which is then used along with `benchmark_configs` to initialize :py:class:`~.BenchmarkCase` instances.

    :param file: File to save results to.
    :param name: Name of the benchmark set.
    :param description: Description of the benchmark set. The same description is used for benchmark cases.
    :param db_uri: URI of the database to benchmark
    :param benchmark_configs: Mapping from case names to configs.
    :param exist_ok: Whether to continue if the file already exists.
    """
    save_results_to_file(
        [
            BenchmarkCase(
                name=case_name,
                description=description,
                db_factory=DBFactory(uri=db_uri),
                benchmark_config=benchmark_config,
            )
            for case_name, benchmark_config in benchmark_configs.items()
        ],
        file,
        name,
        description,
        exist_ok=exist_ok,
    )


def report(
    db_uris: tp.Dict[str, str],
    benchmark_config: BenchmarkConfig = BenchmarkConfig(),
):
    """
    Benchmark DBs with a config and print results to stdout.

    Printed stats contain benchmark config, object sizes, average benchmark values for successful cases and
    exception message for unsuccessful cases.

    :param db_uris: A mapping from DB names to DB uris. DB names are used as names for benchmark cases.
    :param benchmark_config: Benchmark config to use in all benchmark cases.
    """
    benchmark_cases = [
        BenchmarkCase(
            name=db_name,
            db_factory=DBFactory(uri=db_uri),
            benchmark_config=benchmark_config,
        )
        for db_name, db_uri in db_uris.items()
    ]
    sizes = benchmark_config.sizes()
    starting_context_size = sizes["starting_context_size"]
    final_context_size = sizes["final_context_size"]
    misc_size = sizes["misc_size"]
    message_size = sizes["message_size"]

    benchmark_config_report = (
        f"Number of contexts: {benchmark_config.context_num}\n"
        f"From dialog len: {benchmark_config.from_dialog_len}\n"
        f"To dialog len: {benchmark_config.to_dialog_len}\n"
        f"Step dialog len: {benchmark_config.step_dialog_len}\n"
        f"Message misc dimensions: {benchmark_config.message_dimensions}\n"
        f"Misc dimensions: {benchmark_config.misc_dimensions}\n"
        f"Size of misc field: {misc_size} ({naturalsize(misc_size, gnu=True)})\n"
        f"Size of one message: {message_size} ({naturalsize(message_size, gnu=True)})\n"
        f"Starting context size: {starting_context_size} ({naturalsize(starting_context_size, gnu=True)})\n"
        f"Final context size: {final_context_size} ({naturalsize(final_context_size, gnu=True)})"
    )

    line_separator = "-" * 80

    print(f"Starting benchmarking with following parameters:\n{benchmark_config_report}")

    report_result = f"\n{line_separator}\n".join(["", "DB benchmark", benchmark_config_report, ""])

    for benchmark_case in benchmark_cases:
        result = benchmark_case.run()
        report_result += f"\n{line_separator}\n".join(
            [
                benchmark_case.name,
                "".join(
                    [
                        f"{metric.title() + ': ' + str(result['average_results']['pretty_' + metric]):20}"
                        if result["success"]
                        else result["result"]
                        for metric in ("write", "read", "update", "read+update")
                    ]
                ),
                "",
            ]
        )

    print(report_result, end="")
