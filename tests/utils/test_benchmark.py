from copy import deepcopy
import json
import pathlib

import pytest

try:
    from jsonschema import validate

    import dff.utils.benchmark.context_storage as bm
    from dff.context_storages import JSONContextStorage
except ImportError:
    pytest.skip(reason="`dff[benchmark,tests]` not installed", allow_module_level=True)


ROOT_DIR = pathlib.Path(__file__).parent.parent.parent


def test_get_dict():
    assert bm.get_dict(()) == {}
    assert bm.get_dict((1,)) == {0: ""}
    assert bm.get_dict((2, 3)) == {0: "...", 1: "..."}
    assert bm.get_dict((2, 3, 4)) == {0: {0: "....", 1: "....", 2: "...."}, 1: {0: "....", 1: "....", 2: "...."}}


def test_get_context():
    context = bm.get_context(2, (1, 2), (2, 3))
    assert context == bm.Context(
        id=context.id,
        labels={0: ("flow_0", "node_0"), 1: ("flow_1", "node_1")},
        requests={0: bm.Message(misc={0: ".."}), 1: bm.Message(misc={0: ".."})},
        responses={0: bm.Message(misc={0: ".."}), 1: bm.Message(misc={0: ".."})},
        misc={0: "...", 1: "..."},
    )


def test_benchmark_config():
    config = bm.BenchmarkConfig(
        from_dialog_len=1, to_dialog_len=5, message_dimensions=(2, 2), misc_dimensions=(3, 3, 3)
    )
    context = config.get_context()
    actual_context = bm.get_context(1, (2, 2), (3, 3, 3))
    actual_context.id = context.id
    assert context == actual_context

    sizes = config.sizes()
    for size in ("starting_context_size", "final_context_size", "misc_size", "message_size"):
        assert isinstance(sizes[size], int)
        assert sizes[size] > 0

    context_updater = config.get_context_updater()

    contexts = [context]

    while contexts[-1] is not None:
        contexts.append(context_updater(deepcopy(contexts[-1])))

    assert len(contexts) == 5

    for index, context in enumerate(contexts):
        if context is not None:
            assert len(context.labels) == len(context.requests) == len(context.responses) == index + 1

            actual_context = bm.get_context(index + 1, (2, 2), (3, 3, 3))
            actual_context.id = context.id
            assert context == actual_context


def test_context_updater_with_steps():
    config = bm.BenchmarkConfig(
        from_dialog_len=1, to_dialog_len=11, step_dialog_len=3, message_dimensions=(2, 2), misc_dimensions=(3, 3, 3)
    )

    context_updater = config.get_context_updater()

    contexts = [config.get_context()]

    while contexts[-1] is not None:
        contexts.append(context_updater(deepcopy(contexts[-1])))

    assert len(contexts) == 5

    for index, context in zip(range(1, 11, 3), contexts):
        if context is not None:
            assert len(context.labels) == len(context.requests) == len(context.responses) == index

            actual_context = bm.get_context(index, (2, 2), (3, 3, 3))
            actual_context.id = context.id
            assert context == actual_context


def test_db_factory(tmp_path):
    factory = bm.DBFactory(uri=f"json://{tmp_path}/json.json")

    db = factory.db()

    assert isinstance(db, JSONContextStorage)


@pytest.fixture
def context_storage(tmp_path) -> JSONContextStorage:
    factory = bm.DBFactory(uri=f"json://{tmp_path}/json.json")

    return factory.db()


def test_time_context_read_write(context_storage):
    config = bm.BenchmarkConfig(
        context_num=5,
        from_dialog_len=1,
        to_dialog_len=11,
        step_dialog_len=3,
        message_dimensions=(2, 2),
        misc_dimensions=(3, 3, 3),
    )

    results = bm.time_context_read_write(
        context_storage, config.get_context(), config.context_num, config.get_context_updater()
    )

    assert len(context_storage) == 0

    assert len(results) == 3

    write, read, update = results

    assert len(write) == len(read) == len(update) == config.context_num

    assert all([isinstance(write_time, float) and write_time > 0 for write_time in write])

    for read_item in read:
        assert list(read_item.keys()) == list(range(1, 11, 3))
        assert all([isinstance(read_time, float) and read_time > 0 for read_time in read_item.values()])

    for update_item in update:
        assert list(update_item.keys()) == list(range(1, 11, 3))[1:]
        assert all([isinstance(update_time, float) and update_time > 0 for update_time in update_item.values()])


def test_time_context_read_write_without_updates(context_storage):
    config = bm.BenchmarkConfig(
        context_num=5,
        from_dialog_len=1,
        to_dialog_len=2,
        step_dialog_len=3,
        message_dimensions=(2, 2),
        misc_dimensions=(3, 3, 3),
    )

    results = bm.time_context_read_write(
        context_storage,
        config.get_context(),
        config.context_num,
        None,
    )
    _, read, update = results

    assert list(read[0].keys()) == [1]
    assert list(update[0].keys()) == []

    results = bm.time_context_read_write(
        context_storage,
        config.get_context(),
        config.context_num,
        config.get_context_updater(),  # context updater returns None
    )
    _, read, update = results

    assert list(read[0].keys()) == [1]
    assert list(update[0].keys()) == []


def test_average_results():
    benchmark = {
        "success": False,
        "result": "error",
    }

    bm.BenchmarkCase.set_average_results(benchmark)

    assert "average_results" not in benchmark

    benchmark = {
        "success": True,
        "result": {
            "write_times": [1, 2],
            "read_times": [{0: 3, 1: 4}, {0: 5, 1: 6}],
            "update_times": [{0: 7, 1: 8}, {0: 9, 1: 10}],
        },
    }

    bm.BenchmarkCase.set_average_results(benchmark)

    assert benchmark["average_results"] == {
        "average_write_time": 1.5,
        "average_read_time": 4.5,
        "average_update_time": 8.5,
        "read_times_grouped_by_context_num": [3.5, 5.5],
        "read_times_grouped_by_dialog_len": {0: 4, 1: 5},
        "update_times_grouped_by_context_num": [7.5, 9.5],
        "update_times_grouped_by_dialog_len": {0: 8, 1: 9},
        "pretty_write": 1.5,
        "pretty_read": 4.5,
        "pretty_update": 8.5,
        "pretty_read+update": 13,
    }

    benchmark = {
        "success": True,
        "result": {
            "write_times": [1, 2],
            "read_times": [{0: 3}, {0: 5}],
            "update_times": [{}, {}],
        },
    }

    bm.BenchmarkCase.set_average_results(benchmark)


def test_benchmark_case(tmp_path):
    case = bm.BenchmarkCase(
        name="",
        db_factory=bm.DBFactory(uri=f"json://{tmp_path}/json.json"),
        benchmark_config=bm.BenchmarkConfig(
            context_num=5,
            from_dialog_len=1,
            to_dialog_len=11,
            step_dialog_len=3,
            message_dimensions=(2, 2),
            misc_dimensions=(3, 3, 3),
        ),
    )

    benchmark = case.run()
    assert benchmark["success"]

    assert all([isinstance(write_time, float) and write_time > 0 for write_time in benchmark["result"]["write_times"]])

    for read_item in benchmark["result"]["read_times"]:
        assert list(read_item.keys()) == list(range(1, 11, 3))
        assert all([isinstance(read_time, float) and read_time > 0 for read_time in read_item.values()])

    for update_item in benchmark["result"]["update_times"]:
        assert list(update_item.keys()) == list(range(1, 11, 3))[1:]
        assert all([isinstance(update_time, float) and update_time > 0 for update_time in update_item.values()])


def test_save_to_file(tmp_path):
    with open(ROOT_DIR / "utils/db_benchmark/benchmark_schema.json", "r", encoding="utf-8") as fd:
        schema = json.load(fd)

    bm.benchmark_all(
        tmp_path / "result.json",
        "test",
        "test",
        f"json://{tmp_path}/json.json",
        {
            "config": bm.BenchmarkConfig(
                context_num=5,
                from_dialog_len=1,
                to_dialog_len=11,
                step_dialog_len=3,
                message_dimensions=(2, 2),
                misc_dimensions=(3, 3, 3),
            )
        },
    )

    with open(tmp_path / "result.json", "r", encoding="utf-8") as fd:
        benchmark_set = json.load(fd)

    assert set(benchmark_set.keys()) == {"name", "description", "uuid", "benchmarks"}

    benchmark = tuple(benchmark_set["benchmarks"])[0]

    assert set(benchmark.keys()) == {
        "name",
        "db_factory",
        "benchmark_config",
        "uuid",
        "description",
        "sizes",
        "success",
        "result",
        "average_results",
    }

    validate(instance=benchmark_set, schema=schema)

    bm.benchmark_all(
        tmp_path / "result_unsuccessful.json",
        "test",
        "test",
        "None",
        {
            "config": bm.BenchmarkConfig(
                context_num=5,
                from_dialog_len=1,
                to_dialog_len=11,
                step_dialog_len=3,
                message_dimensions=(2, 2),
                misc_dimensions=(3, 3, 3),
            )
        },
    )

    with open(tmp_path / "result_unsuccessful.json", "r", encoding="utf-8") as fd:
        benchmark_set = json.load(fd)

    assert not benchmark_set["benchmarks"][0]["success"]
    assert "average_results" not in benchmark_set["benchmarks"][0]

    validate(instance=benchmark_set, schema=schema)
