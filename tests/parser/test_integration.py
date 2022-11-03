"""Test parser as a whole."""
import sys
from pathlib import Path
from filecmp import dircmp
from copy import copy
from itertools import product
from typing import List

import pytest

from dff.script.import_export.parser.utils.exceptions import ScriptValidationError
from dff.script.import_export.parser import dependencies, py2yaml_cli, yaml2py_cli, py2graph_cli, graph2py_cli
import dff

true_dependencies = copy(dependencies)


TEST_DIR = Path(__file__).parent / "TEST_CASES"


def assert_dirs_equal(dir1: Path, dir2: Path):
    subdir_stack: List[str] = []

    def _assert_dir_eq(dir_cmp: dircmp):
        assert len(dir_cmp.left_only) == 0
        assert len(dir_cmp.right_only) == 0
        for diff_file in dir_cmp.diff_files:
            with open(dir1.joinpath(*subdir_stack, diff_file), "r") as first, open(
                dir2.joinpath(*subdir_stack, diff_file), "r"
            ) as second:
                assert list(first.readlines()) == list(second.readlines())
        for name, subdir in dir_cmp.subdirs.items():
            subdir_stack.append(name)
            _assert_dir_eq(subdir)
            subdir_stack.pop()

    _assert_dir_eq(dircmp(dir1, dir2))


py2yaml_params = [
    *[
        (
            TEST_DIR / "test_py2yaml" / "simple_tests" / f"test_{test_number}" / "python_files",
            TEST_DIR / "test_py2yaml" / "simple_tests" / f"test_{test_number}" / "python_files" / "main.py",
            TEST_DIR / "test_py2yaml" / "simple_tests" / f"test_{test_number}" / "yaml_files",
            exception,
        )
        for test_number, exception in zip(
            range(0, 19),
            [
                SystemExit,
                None,
                ScriptValidationError,
                ScriptValidationError,
                ScriptValidationError,
                ScriptValidationError,
                ScriptValidationError,
                ScriptValidationError,
                None,
                None,
                None,
                None,
                ScriptValidationError,
                None,
                None,
                ScriptValidationError,
                None,
                None,
                None,
            ],
        )
    ],
    *[
        (
            TEST_DIR / "test_py2yaml" / "complex_tests" / f"test_{test_number}" / "python_files",
            TEST_DIR / "test_py2yaml" / "complex_tests" / f"test_{test_number}" / "python_files" / "main.py",
            TEST_DIR / "test_py2yaml" / "complex_tests" / f"test_{test_number}" / "yaml_files",
            exception,
        )
        for test_number, exception in zip(range(1, 4), [None, None, None])
    ],
]


@pytest.mark.parametrize(
    "project_root_dir,main_file,output_dir,exception,nx_available",
    list((*x[0], x[1]) for x in product(py2yaml_params, [True, False])),  # add True or False to each param set
)
def test_py2yaml(project_root_dir, main_file, output_dir, exception, nx_available, tmp_path, monkeypatch):
    """Test the py2yaml part of the parser."""
    if not true_dependencies["graph"] and nx_available:
        pytest.skip("`networkx` is not installed")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dff.py2yaml",
            str(main_file),
            str(project_root_dir),
            str(tmp_path / "script.yaml"),
        ],
    )

    def _test_py2yaml():
        py2yaml_cli()
        assert_dirs_equal(output_dir, tmp_path)

    monkeypatch.setitem(dff.script.import_export.parser.dependencies, "graph", nx_available)
    if exception:
        with pytest.raises(exception):
            _test_py2yaml()
    else:
        _test_py2yaml()


yaml2py_params = [
    *[
        (
            TEST_DIR / "test_yaml2py" / "simple_tests" / f"test_{test_number}" / "yaml_files" / "script.yaml",
            TEST_DIR / "test_yaml2py" / "simple_tests" / f"test_{test_number}" / "python_files",
            exception,
        )
        for test_number, exception in zip(
            range(1, 6),
            [
                None,
                None,
                None,
                None,
                None,
            ],
        )
    ],
    *[
        (
            TEST_DIR / "test_yaml2py" / "complex_tests" / f"test_{test_number}" / "yaml_files" / "script.yaml",
            TEST_DIR / "test_yaml2py" / "complex_tests" / f"test_{test_number}" / "python_files",
            exception,
        )
        for test_number, exception in zip(range(1, 4), [None, None, None])
    ],
]


@pytest.mark.parametrize(
    "script,output_dir,exception",
    yaml2py_params,
)
def test_yaml2py(script, output_dir, exception, tmp_path, monkeypatch):
    """Test yaml2py

    :param script: Yaml script to convert
    :param output_dir: Directory with a correct answer
    :param exception: Exception raised during converting
    :param tmp_path: Temporary path to convert to
    :return:
    """
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dff.yaml2py",
            str(script),
            str(tmp_path),
        ],
    )

    def _test_yaml2py():
        yaml2py_cli()
        assert_dirs_equal(output_dir, tmp_path)

    if exception:
        with pytest.raises(exception):
            _test_yaml2py()
    else:
        _test_yaml2py()


py2graph_params = [
    *[
        (
            TEST_DIR / "test_py2graph" / "complex_tests" / f"test_{test_number}" / "python_files",
            TEST_DIR / "test_py2graph" / "complex_tests" / f"test_{test_number}" / "python_files" / "main.py",
            TEST_DIR / "test_py2graph" / "complex_tests" / f"test_{test_number}" / "graph_files",
            exception,
        )
        for test_number, exception in zip(range(1, 3), [None, None])
    ],
]


@pytest.mark.parametrize(
    "project_root_dir,main_file,output,exception",
    py2graph_params,
)
@pytest.mark.skipif(not true_dependencies["graph"], reason="`networkx` is not installed")
def test_py2graph(project_root_dir, main_file, output, exception, tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dff.py2graph",
            str(main_file),
            str(project_root_dir),
            str(tmp_path / "graph.json"),
        ],
    )

    def _test_yaml2py():
        py2graph_cli()
        assert_dirs_equal(output, tmp_path)

    if exception:
        with pytest.raises(exception):
            _test_yaml2py()
    else:
        _test_yaml2py()


graph2py_params = [
    *[
        (
            TEST_DIR / "test_graph2py" / "complex_tests" / f"test_{test_number}" / "graph_files" / "graph.json",
            TEST_DIR / "test_graph2py" / "complex_tests" / f"test_{test_number}" / "python_files",
            exception,
        )
        for test_number, exception in zip(range(1, 2), [None])
    ],
]


@pytest.mark.parametrize(
    "input_file,output_dir,exception",
    graph2py_params,
)
@pytest.mark.skipif(not true_dependencies["graph"], reason="`networkx` is not installed")
def test_graph2py(input_file, output_dir, exception, tmp_path, monkeypatch):
    """Test graph2py

    :param input_file: Graph file to convert
    :param output_dir: Directory with a correct answer
    :param exception: Exception raised during converting
    :param tmp_path: Temporary path to convert to
    :return:
    """
    monkeypatch.setattr(sys, "argv", ["dff.graph2py", str(input_file), str(tmp_path)])

    def _test_graph2py():
        graph2py_cli()
        assert_dirs_equal(output_dir, tmp_path)

    if exception:
        with pytest.raises(exception):
            _test_graph2py()
    else:
        _test_graph2py()
