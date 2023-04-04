from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

import pytest

from dff.utils.parser.dff_project import DFFProject
from tests.parser.utils import assert_dirs_equal, assert_files_equal

TEST_DIR = Path(__file__).parent / "TEST_CASES"

ENGINE_TUTORIAL_DIR = Path(__file__).parent.parent.parent / "tutorials" / "script" / "core"


# todo: add more parameters?
@pytest.mark.parametrize("test_case", [str(working_dir) for working_dir in (TEST_DIR / "complex_cases").iterdir()])
def test_conversions(test_case: str, tmp_path):
    working_dir = Path(test_case)
    python_dir = working_dir / "python_files"
    main_file = python_dir / "main.py"
    yaml_script = working_dir / "script.yaml"
    graph_script = working_dir / "graph.json"

    # from_python -> to_yaml & to_graph
    dff_project = DFFProject.from_python(python_dir, main_file)
    dff_project.to_yaml(tmp_path / "script.yaml")
    dff_project.to_graph(tmp_path / "graph.json")
    assert_files_equal(tmp_path / "script.yaml", yaml_script)
    assert_files_equal(tmp_path / "graph.json", graph_script)

    # from_yaml -> to_graph
    dff_project = DFFProject.from_yaml(yaml_script)
    dff_project.to_graph(tmp_path / "graph.json")
    assert_files_equal(tmp_path / "graph.json", graph_script)

    # from_graph -> to_yaml
    dff_project = DFFProject.from_graph(graph_script)
    dff_project.to_yaml(tmp_path / "script.yaml")
    assert_files_equal(tmp_path / "script.yaml", yaml_script)

    # from_yaml(new_script) -> to_python

    dff_project = DFFProject.from_yaml(working_dir / "new_script.yaml")

    # test creating
    with TemporaryDirectory() as tmpdir:
        created = Path(tmpdir)
        dff_project.to_python(created)

        assert_dirs_equal(working_dir / "result_creating", created)

    # test editing
    with TemporaryDirectory() as tmpdir:
        edited = Path(copytree(working_dir / "python_files", tmpdir + "/edited"))

        dff_project.to_python(edited)

        assert_dirs_equal(working_dir / "result_editing", edited)


@pytest.mark.parametrize(
    "tutorial_name",
    [
        "1_basics",
        "2_conditions",
        "3_responses",
        "4_transitions",
        "5_global_transitions",
        "6_context_serialization",
        "7_pre_response_processing",
        "8_misc",
        "9_pre_transitions_processing",
    ],
)
def test_core_tutorials(tutorial_name: str, tmp_path):
    python_name = tutorial_name + ".py"

    dff_project = DFFProject.from_python(
        ENGINE_TUTORIAL_DIR, (ENGINE_TUTORIAL_DIR / python_name), script_initializer="pipeline"
    )

    dff_project.to_yaml(tmp_path / (tutorial_name + ".yaml"))

    assert_files_equal(tmp_path / (tutorial_name + ".yaml"), TEST_DIR / "core_tutorials" / (tutorial_name + ".yaml"))

    dff_project = DFFProject.from_yaml(tmp_path / (tutorial_name + ".yaml"))

    dff_project.to_graph(tmp_path / (tutorial_name + ".json"))

    assert_files_equal(tmp_path / (tutorial_name + ".json"), TEST_DIR / "core_tutorials" / (tutorial_name + ".json"))

    dff_project = DFFProject.from_graph(tmp_path / (tutorial_name + ".json"))

    dff_project.to_python(tmp_path)

    assert_files_equal((tmp_path / python_name), TEST_DIR / "core_tutorials" / python_name)
