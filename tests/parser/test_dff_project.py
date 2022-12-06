from pathlib import Path

from dff.script.parser.dff_project import DFFProject
from dff.script.parser.base_parser_object import String


def test_from_python():
    project_dir = Path("tests/parser/TEST_CASES/just_works/python_files")
    dff_project = DFFProject.from_python(project_dir, project_dir / "main.py")

    assert str(dff_project["main"]["actor"].resolve_path(["func"]).resolve_name) == "dff.core.engine.core.Actor"
    assert set(dff_project.children.keys()) == {"flow", "main", "functions", "transitions"}

    assert dff_project.script[0] == dff_project["main"]["script"]
    assert str(dff_project.script[1]) == "('global_flow', 'start_node')"
    assert str(dff_project.script[2]) == "('global_flow', 'fallback_node')"


def test_resolved_script():
    project_dir = Path("tests/parser/TEST_CASES/just_works/python_files")
    dff_project = DFFProject.from_python(project_dir, project_dir / "main.py")

    resolved_script = dff_project.resolved_script

    assert resolved_script['dff.core.engine.core.keywords.GLOBAL']['dff.core.engine.core.keywords.MISC'][String("var1")] == String("global_data")
