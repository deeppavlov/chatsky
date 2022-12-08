from pathlib import Path

import pytest

from dff.script.parser.dff_project import DFFProject
from dff.script.parser.base_parser_object import String
from .utils import assert_dirs_equal, assert_files_equal

TEST_DIR = Path(__file__).parent / "TEST_CASES"


def test_from_python():
    project_dir = Path("tests/parser/TEST_CASES/just_works/python_files")
    dff_project = DFFProject.from_python(project_dir, project_dir / "main.py")

    assert str(dff_project["main"]["actor"].resolve_path(["func"]).resolve_name) == "dff.core.engine.core.Actor"
    assert set(dff_project.children.keys()) == {"flow", "main", "functions", "transitions"}

    assert dff_project.script[0] == dff_project["main"]["script"]
    assert dff_project.script[1][0] == "'global_flow'"
    assert dff_project.script[1][1] == "'start_node'"
    assert dff_project.script[2][0] == "'global_flow'"
    assert dff_project.script[2][1] == "'fallback_node'"


def test_resolved_script():
    project_dir = Path("tests/parser/TEST_CASES/just_works/python_files")
    dff_project = DFFProject.from_python(project_dir, project_dir / "main.py")

    resolved_script = dff_project.resolved_script

    assert resolved_script['dff.core.engine.core.keywords.GLOBAL'][None]['MISC']["'var1'"] == String("global_data")


@pytest.mark.parametrize(
    "test_case",
    [
        TEST_DIR / "just_works",
    ]
)
def test_conversions(test_case: Path, tmp_path):  # todo: when to_python is implemented pass those methods as params
    python_dir = test_case / "python_files"
    main_file = python_dir / "main.py"
    yaml_script = test_case / "yaml_files" / "script.yaml"
    graph_script = test_case / "graph_files" / "graph.json"

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
