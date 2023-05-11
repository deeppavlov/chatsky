"""
Generate results for test cases.
"""
from pathlib import Path
from shutil import rmtree, copytree
import difflib

from dff.utils.parser.dff_project import DFFProject


TEST_DIR = Path(__file__).parent / "TEST_CASES"


def rebuild_complex_cases():
    """
    Generate new files for each `complex_case` inside the `TEST_DIR / complex_cases` directory.
    The generated files are used to test that the parser is working correctly as well as showcase parser capabilities.

    Expected structure of directories inside `TEST_DIR / complex_cases`:
        - `python_files` directory containing dff project.
        - `new_script.yaml` file -- an edited dff project.

    The function generates new files inside such directories:
        - `script.yaml` -- a yaml representation of files in `python_files` (`to_yaml(python_files)`).
        - `graph.json` -- a graph representation of files in `python_files` (`to_graph(python_files)`).
        - `script.yaml.diff` -- a diff file for `script.yaml` and `new_script.yaml`.
        - `result_creating` directory -- a python representation of `new_script.yaml` (`to_python(new_script.yaml)`).
        - `result_editing` directory -- a result of editing `new_script.yaml` over `python_files`
          (`to_python(new_script.yaml) -> python_files`).

    :raises RuntimeError:
        If the directory is missing a required file.
    """
    for working_dir in (TEST_DIR / "complex_cases").iterdir():
        if not working_dir.is_dir():
            continue

        # Generate script.yaml and graph.json

        python_dir = working_dir / "python_files"
        main_file = python_dir / "main.py"

        if not python_dir.exists():
            raise RuntimeError(f"Python dir {python_dir} not found.")

        if not main_file.exists():
            raise RuntimeError(f"Main file {main_file} not found.")

        dff_project = DFFProject.from_python(python_dir, main_file)

        dff_project.to_yaml(working_dir / "script.yaml")
        dff_project.to_graph(working_dir / "graph.json")

        # Generate diff file

        with open(working_dir / "script.yaml", "r") as fd:
            original = fd.readlines()

        new_script = working_dir / "new_script.yaml"

        if not new_script.exists():
            raise RuntimeError(f"Edited script {new_script} not found.")

        with open(new_script, "r") as fd:
            new = fd.readlines()

        diff = difflib.ndiff(original, new)

        with open(working_dir / "script.yaml.diff", "w") as fd:
            fd.write("".join(diff))

        # Generate results of to_python

        dff_project = DFFProject.from_yaml(working_dir / "new_script.yaml")

        creation_dir = working_dir / "result_creating"

        if creation_dir.exists():
            rmtree(creation_dir)
            creation_dir.mkdir(exist_ok=True)

        editing_dir = working_dir / "result_editing"

        if editing_dir.exists():
            rmtree(editing_dir)
        copytree(working_dir / "python_files", editing_dir)

        dff_project.to_python(working_dir / "result_creating")
        dff_project.to_python(working_dir / "result_editing")


def rebuild_core_tutorials():
    """
    Generate results of applying parser to `script/core` tutorials.

    The results are represented by three files for each tutorial:
    1. `tutorial_name.json` is a result of :py:meth:`~.DFFProject.to_graph`.
    2. `tutorial_name.py` is a result of :py:meth:`~.DFFProject.to_python`.
    3. `tutorial_name.yaml` is a result of :py:meth:`~.DFFProject.to_yaml`.

    All the generated files are stored inside the `tests/parser/TEST_CASES/core_tutorials` directory.
    """
    engine_tutorial_dir = Path("tutorials/script/core")

    test_dir = TEST_DIR / "core_tutorials"

    if test_dir.exists():
        rmtree(test_dir)
    test_dir.mkdir(parents=True)

    for file in engine_tutorial_dir.iterdir():
        if file.is_file():
            dff_project = DFFProject.from_python(engine_tutorial_dir, file, script_initializer="pipeline")

            dff_project.to_python(test_dir)
            dff_project.to_yaml(test_dir / (file.stem + ".yaml"))
            dff_project.to_graph(test_dir / (file.stem + ".json"))


if __name__ == "__main__":
    rebuild_complex_cases()
    rebuild_core_tutorials()
