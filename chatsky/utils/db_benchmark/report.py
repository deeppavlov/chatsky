"""
Report
--------
This method contains a function to print benchmark results to console.
"""

from pathlib import Path
from typing import Union, Set, Literal
import json


def report(
    file: Union[str, Path],
    display: Set[Literal["name", "desc", "config", "metrics"]] = set({"name", "metrics"}),
):
    """
    Print average results from a result file to stdout.

    Printed stats contain benchmark configs, object sizes, average benchmark values for successful cases and
    exception message for unsuccessful cases.

    :param file:
        File with benchmark results generated by
        :py:func:`~chatsky.utils.db_benchmark.benchmark.save_results_to_file`.
    :param display:
        A set of objects to display in results.
        Values allowed inside the set:

            - "name" -- displays the name of the benchmark case.
            - "desc" -- displays the description of the benchmark case.
            - "config" -- displays the config info of the benchmark case.
            - "metrics" -- displays average write, read, update read+update times.
    """
    with open(file, "r", encoding="utf-8") as fd:
        file_contents = json.load(fd)

    sep = "-" * 80

    report_result = "\n".join([sep, file_contents["name"], sep, file_contents["description"], sep, ""])

    for benchmark in file_contents["benchmarks"]:
        reported_values = {
            "name": benchmark["name"],
            "desc": benchmark["description"],
            "config": "\n".join(f"{k}: {v}" for k, v in benchmark["benchmark_config"].items()),
            "metrics": "".join(
                [
                    (
                        f"{metric.title() + ': ' + str(benchmark['average_results']['pretty_' + metric]):20}"
                        if benchmark["success"]
                        else benchmark["result"]
                    )
                    for metric in ("write", "read", "update", "read+update")
                ]
            ),
        }

        result = []
        for value_name, value in reported_values.items():
            if value_name in display:
                result.append(value)
        result.append("")

        report_result += f"\n{sep}\n".join(result)

    print(report_result, end="")
