from pathlib import Path
from shutil import copytree

import pytest

from dff.utils.parser.dff_project import DFFProject
from .utils import assert_dirs_equal, assert_files_equal

TEST_DIR = Path(__file__).parent / "TEST_CASES"
ENGINE_EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples" / "script" / "core"


# todo: add more parameters?
@pytest.mark.parametrize(
    "test_case",
    [
        working_dir for working_dir in (TEST_DIR / "conversions").iterdir()
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
        working_dir for working_dir in (TEST_DIR / "to_python").iterdir()
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


@pytest.mark.parametrize(
    "example_name",
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
def test_engine_examples(example_name: str, tmp_path):
    python_name = example_name + ".py"

    dff_project = DFFProject.from_python(ENGINE_EXAMPLES_DIR, (ENGINE_EXAMPLES_DIR / python_name), script_initializer="pipeline")

    dff_project.to_yaml(tmp_path / (example_name + ".yaml"))

    assert_files_equal(tmp_path / (example_name + ".yaml"), TEST_DIR / "engine_examples" / (example_name + ".yaml"))

    dff_project = DFFProject.from_yaml(tmp_path / (example_name + ".yaml"))

    dff_project.to_graph(tmp_path / (example_name + ".json"))

    assert_files_equal(tmp_path / (example_name + ".json"), TEST_DIR / "engine_examples" / (example_name + ".json"))

    dff_project = DFFProject.from_graph(tmp_path / (example_name + ".json"))

    dff_project.to_python(tmp_path)

    assert_files_equal((tmp_path / python_name), TEST_DIR / "engine_examples" / python_name)
