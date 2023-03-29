from pathlib import Path
from shutil import rmtree, copytree
import difflib
from sys import version_info

from dff.utils.parser.dff_project import DFFProject
from dff.utils.parser.base_parser_object import remove_suffix

if version_info >= (3, 9):
    TEST_DIR = Path("tests/parser/TEST_CASES/PYTHON3.9+")
else:
    TEST_DIR = Path("tests/parser/TEST_CASES/PYTHON3.8-")


def rebuild_conversions():
    for working_dir in (TEST_DIR / "conversions").iterdir():
        if working_dir.is_dir():
            dff_project = DFFProject.from_python(working_dir / "python_files", working_dir / "python_files" / "main.py")

            dff_project.to_yaml(working_dir / "script.yaml")
            dff_project.to_graph(working_dir / "graph.json")


def rebuild_to_python_tests():
    for working_dir in (TEST_DIR / "to_python").iterdir():
        if working_dir.is_dir():
            # GENERATE OLD SCRIPT
            unedited = DFFProject.from_python(working_dir / "initial_files", working_dir / "initial_files" / "main.py")

            unedited.to_yaml(working_dir / "old_script.yaml")

            # GENERATE DIFF FILE

            with open(working_dir / "old_script.yaml", "r") as fd:
                original = fd.readlines()

            with open(working_dir / "script.yaml", "r") as fd:
                new = fd.readlines()

            diff = difflib.ndiff(original, new)

            with open(working_dir / "script.yaml.diff", "w") as fd:
                fd.write("".join(diff))

            # GENERATE RESULTS OF TO_PYTHON

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
    engine_tutorial_dir = Path("tutorials/script/core")

    test_dir = TEST_DIR / "engine_examples"

    if test_dir.exists():
        rmtree(test_dir)
    test_dir.mkdir(parents=True)

    for file in engine_tutorial_dir.iterdir():
        if file.is_file():
            dff_project = DFFProject.from_python(engine_tutorial_dir, file, script_initializer="pipeline")

            dff_project.to_python(test_dir)
            dff_project.to_yaml(test_dir / (remove_suffix(file.parts[-1], ".py") + ".yaml"))
            dff_project.to_graph(test_dir / (remove_suffix(file.parts[-1], ".py") + ".json"))


if __name__ == "__main__":
    rebuild_conversions()
    rebuild_to_python_tests()
    rebuild_engine_examples()
