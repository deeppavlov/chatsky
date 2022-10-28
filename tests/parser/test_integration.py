"""Test parser as a whole."""
from io import StringIO
from pathlib import Path
from filecmp import dircmp
from copy import copy
from itertools import product

import pytest

from dff.script.import_export.parser.dumpers_loaders import yaml_dumper_loader
from dff.script.import_export.parser.processors.recursive_parser import RecursiveParser
from dff.script.import_export.parser.utils.exceptions import ScriptValidationError
from dff.script.import_export.parser import dependencies, py2yaml, yaml2py, py2graph, graph2py
import dff

true_dependencies = copy(dependencies)


current_dir = Path(__file__).parent


py2yaml_params = [
    *[
        (
            current_dir / "test_py2yaml" / "simple_tests" / f"test_{test_number}" / "python_files",
            current_dir / "test_py2yaml" / "simple_tests" / f"test_{test_number}" / "python_files" / "main.py",
            current_dir / "test_py2yaml" / "simple_tests" / f"test_{test_number}" / "yaml_files" / "script.yaml",
            exception,
        )
        for test_number, exception in zip(
            range(1, 18),
            [
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
            ],
        )
    ],
    *[
        (
            current_dir / "test_py2yaml" / "complex_tests" / f"test_{test_number}" / "python_files",
            current_dir / "test_py2yaml" / "complex_tests" / f"test_{test_number}" / "python_files" / "main.py",
            current_dir / "test_py2yaml" / "complex_tests" / f"test_{test_number}" / "yaml_files" / "script.yaml",
            exception,
        )
        for test_number, exception in zip(range(1, 4), [None, None, None])
    ],
]


@pytest.mark.parametrize(
    "project_root_dir,main_file,script,exception,nx_available",
    list((*x[0], x[1]) for x in product(py2yaml_params, [True, False]))  # add True or False to each param set
)
def test_py2yaml(project_root_dir, main_file, script, exception, nx_available):
    """Test the py2yaml part of the parser."""
    if not true_dependencies["graph"] and nx_available:
        pytest.skip("`networkx` is not installed")
    def _test_py2yaml():
        buffer = StringIO()
        recursive_parser = RecursiveParser(Path(project_root_dir))
        recursive_parser.parse_project_dir(Path(main_file))
        yaml_dumper_loader.dump(recursive_parser.to_dict(), buffer)
        buffer.seek(0)
        with open(script, "r", encoding="utf-8") as correct_result:
            assert buffer.read() == correct_result.read()

    dff.script.import_export.parser.dependencies["graph"] = nx_available
    if exception:
        with pytest.raises(exception):
            _test_py2yaml()
    else:
        _test_py2yaml()
    dff.script.import_export.parser.dependencies["graph"] = true_dependencies["graph"]


yaml2py_params = [
    *[
        (
            current_dir / "test_yaml2py" / "simple_tests" / f"test_{test_number}" / "yaml_files" / "script.yaml",
            current_dir / "test_yaml2py" / "simple_tests" / f"test_{test_number}" / "python_files",
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
            current_dir / "test_yaml2py" / "complex_tests" / f"test_{test_number}" / "yaml_files" / "script.yaml",
            current_dir / "test_yaml2py" / "complex_tests" / f"test_{test_number}" / "python_files",
            exception,
        )
        for test_number, exception in zip(range(1, 4), [None, None, None])
    ],
]


@pytest.mark.parametrize(
    "script,output_dir,exception",
    yaml2py_params,
)
def test_yaml2py(script, output_dir, exception, tmp_path):
    """Test yaml2py

    :param script: Yaml script to convert
    :param output_dir: Directory with a correct answer
    :param exception: Exception raised during converting
    :param tmp_path: Temporary path to convert to
    :return:
    """

    def _test_yaml2py():
        def _assert_dir_eq(dir_cmp: dircmp):
            """Assert two dirs are equal

            :param dir_cmp:
            :return:
            """
            assert dir_cmp.left_only == []
            assert dir_cmp.right_only == []
            assert dir_cmp.diff_files == []
            for subdir in dir_cmp.subdirs.values():
                _assert_dir_eq(subdir)

        yaml2py(Path(script), tmp_path)
        _assert_dir_eq(dircmp(output_dir, tmp_path))

    if exception:
        with pytest.raises(exception):
            _test_yaml2py()
    else:
        _test_yaml2py()


py2graph_params = [
    *[
        (
            current_dir / "test_py2graph" / "complex_tests" / f"test_{test_number}" / "python_files",
            current_dir / "test_py2graph" / "complex_tests" / f"test_{test_number}" / "python_files" / "main.py",
            current_dir / "test_py2graph" / "complex_tests" / f"test_{test_number}" / "graph_files",
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
def test_py2graph(project_root_dir, main_file, output, exception, tmp_path):
    def _test_yaml2py():
        def _assert_dir_eq(dir_cmp: dircmp):
            """Assert two dirs are equal

            :param dir_cmp:
            :return:
            """
            assert dir_cmp.left_only == []
            assert dir_cmp.right_only == []
            assert dir_cmp.diff_files == []
            for subdir in dir_cmp.subdirs.values():
                _assert_dir_eq(subdir)

        py2graph(main_file, project_root_dir, tmp_path / "graph.json")
        _assert_dir_eq(dircmp(output, tmp_path))

    if exception:
        with pytest.raises(exception):
            _test_yaml2py()
    else:
        _test_yaml2py()


graph2py_params = [
    *[
        (
            current_dir / "test_graph2py" / "complex_tests" / f"test_{test_number}" / "graph_files" / "graph.json",
            current_dir / "test_graph2py" / "complex_tests" / f"test_{test_number}" / "python_files",
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
def test_graph2py(input_file, output_dir, exception, tmp_path):
    """Test graph2py

    :param input_file: Graph file to convert
    :param output_dir: Directory with a correct answer
    :param exception: Exception raised during converting
    :param tmp_path: Temporary path to convert to
    :return:
    """

    def _test_graph2py():
        def _assert_dir_eq(dir_cmp: dircmp):
            """Assert two dirs are equal

            :param dir_cmp:
            :return:
            """
            assert dir_cmp.left_only == []
            assert dir_cmp.right_only == []
            assert dir_cmp.diff_files == []
            for subdir in dir_cmp.subdirs.values():
                _assert_dir_eq(subdir)

        graph2py(Path(input_file), tmp_path)
        _assert_dir_eq(dircmp(output_dir, tmp_path))

    if exception:
        with pytest.raises(exception):
            _test_graph2py()
    else:
        _test_graph2py()
