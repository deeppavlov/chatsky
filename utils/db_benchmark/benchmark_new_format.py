"""
New format
----------
Converts old benchmark result files to new formats
"""
import json
import pathlib
import typing as tp

benchmark_path = pathlib.Path("benchmarks")


def update_benchmark_file(benchmark_set_file: tp.Union[pathlib.Path, str]):
    with open(benchmark_set_file, "r") as fd:
        benchmark_set = json.load(fd)

    # move benchmarks from dict to list
    if isinstance(benchmark_set.get("benchmarks"), dict):
        benchmarks = benchmark_set.pop("benchmarks")
        benchmark_set["benchmarks"] = list(benchmarks.values())

    # update sizes
    for benchmark in benchmark_set["benchmarks"]:
        if "sizes" not in benchmark:
            sizes = {
                key: benchmark.pop(key) for key in (
                    "starting_context_size", "final_context_size", "misc_size", "message_size"
                )
            }

            benchmark["sizes"] = sizes

    with open(benchmark_set_file, "w") as fd:
        json.dump(benchmark_set, fd)


if __name__ == "__main__":
    for file in benchmark_path.iterdir():
        if file.suffix == ".json":
            update_benchmark_file(file)
