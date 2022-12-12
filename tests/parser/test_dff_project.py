from pathlib import Path
from shutil import copytree

import pytest

from dff.script.parser.dff_project import DFFProject
from dff.script.parser.base_parser_object import String
from .utils import assert_dirs_equal, assert_files_equal

TEST_DIR = Path(__file__).parent / "TEST_CASES"


# todo: add more parameters?
@pytest.mark.parametrize(
    "test_case",
    [
        TEST_DIR / "conversions" / "just_works",
        TEST_DIR / "conversions" / "modular",
    ]
)
def test_conversions(test_case: Path, tmp_path):
    python_dir = test_case / "python_files"
    main_file = python_dir / "main.py"
    yaml_script = test_case / "script.yaml"
    graph_script = test_case / "graph.json"

    # from_python
    dff_project = DFFProject.from_python(python_dir, main_file)
    dff_project.to_yaml(tmp_path / "script.yaml")
    dff_project.to_graph(tmp_path / "graph.json")
    assert_files_equal(tmp_path / "script.yaml", yaml_script)
    assert_files_equal(tmp_path / "graph.json", graph_script)

    # from_yaml
    dff_project = DFFProject.from_yaml(yaml_script)
    dff_project.to_graph(tmp_path / "graph.json")
    assert_files_equal(tmp_path / "graph.json", graph_script)

    # from_graph
    dff_project = DFFProject.from_graph(graph_script)
    dff_project.to_yaml(tmp_path / "script.yaml")
    assert_files_equal(tmp_path / "script.yaml", yaml_script)


@pytest.mark.parametrize(
    "test_case",
    [
        TEST_DIR / "to_python" / "just_works",
    ]
)
def test_to_python(test_case: Path, tmp_path):
    dff_project = DFFProject.from_yaml(test_case / "script.yaml")

    # test creation

    created = tmp_path / "created"
    created.mkdir()

    dff_project.to_python(created)

    assert_dirs_equal(test_case / "result_creating", created)

    # test editing

    edited = copytree(test_case / "initial_files", tmp_path / "edited")

    dff_project.to_python(edited)

    assert_dirs_equal(test_case / "result_editing", edited)
