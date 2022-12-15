from pathlib import Path
from shutil import rmtree, copytree

from dff.script.parser.dff_project import DFFProject

TEST_DIR = Path("tests/parser/TEST_CASES")


def rebuild_conversions():
    for working_dir in (TEST_DIR / "conversions").iterdir():
        if working_dir.is_dir():
            dff_project = DFFProject.from_python(working_dir / "python_files", working_dir / "python_files" / "main.py")

            dff_project.to_yaml(working_dir / "script.yaml")
            dff_project.to_graph(working_dir / "graph.json")


def rebuild_to_python_tests():
    for working_dir in (TEST_DIR / "to_python").iterdir():
        if working_dir.is_dir():
            dff_project = DFFProject.from_yaml(working_dir / "script.yaml")

            creation_dir = working_dir / "result_creating"

            if creation_dir.exists():
                rmtree(creation_dir)
                creation_dir.mkdir(exist_ok=True)

            editing_dir = working_dir / "result_editing"

            if editing_dir.exists():
                rmtree(editing_dir)
                copytree(working_dir / "initial_files", editing_dir)

            dff_project.to_python(working_dir / "result_creating")
            dff_project.to_python(working_dir / "result_editing")


def rebuild_engine_examples():
    engine_example_dir = Path("examples/engine")

    for file in engine_example_dir.iterdir():
        if file.is_file():
            dff_project = DFFProject.from_python(engine_example_dir, file)

            dff_project.to_python(TEST_DIR / "engine_examples")
            dff_project.to_yaml(TEST_DIR / "engine_examples" / (file.parts[-1].removesuffix(".py") + ".yaml"))
            dff_project.to_graph(TEST_DIR / "engine_examples" / (file.parts[-1].removesuffix(".py") + ".json"))


if __name__ == "__main__":
    rebuild_conversions()
    rebuild_to_python_tests()
    rebuild_engine_examples()

