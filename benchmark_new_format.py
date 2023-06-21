import json
import pathlib

benchmark_path = pathlib.Path("benchmarks")

for file in benchmark_path.iterdir():
    if file.suffix == ".json":
        with open(file, "r") as fd:
            benchmark_set = json.load(fd)

        non_benchmark_fields = ("name", "description", "uuid", "benchmarks")

        new_benchmark_set = {k: v for k, v in benchmark_set.items() if k in non_benchmark_fields}

        new_benchmark_set["benchmarks"] = {k: v for k, v in benchmark_set.items() if k not in non_benchmark_fields}

        with open(file, "w") as fd:
            json.dump(new_benchmark_set, fd)
