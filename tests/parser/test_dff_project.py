from pathlib import Path

from dff.script.parser.dff_project import DFFProject


def test_from_python():
    project_dir = Path("tests/parser/TEST_CASES/basic_test/python_files")
    dff_project = DFFProject.from_python(project_dir, project_dir / "main.py")

    assert str(dff_project["main"]["actor"].resolve_path(["func"]).resolve_name) == "dff.core.engine.core.Actor"
    assert set(dff_project.children.keys()) == {"flow", "main", "functions", "transitions"}
