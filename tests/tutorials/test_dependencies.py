from typing import TYPE_CHECKING
from docs.source.utils.notebook import InstallationCell
import re
from pathlib import Path

import pytest

if TYPE_CHECKING:
    from pytest_virtualenv import VirtualEnv


PROJECT_ROOT_DIR = Path(__file__).parent.parent.parent
DFF_TUTORIALS_DIR = PROJECT_ROOT_DIR / "tutorials"
DFF_TUTORIAL_PY_FILES = map(str, DFF_TUTORIALS_DIR.glob("./**/*.py"))


def check_tutorial_dependencies(venv: "VirtualEnv", tutorial_source_code: str, tmp_path: "Path"):
    """
    Install dependencies required by a tutorial in `venv` and run the tutorial.

    :param venv: Virtual environment to run the tutorial in.
    :param tutorial_source_code: Source code of the tutorial (unmodified by `apply_replace_patterns`).
    :param tmp_path: Temporary path to save the tutorial to.
    :return:
    """
    tutorial_path = tmp_path / "tutorial.py"

    venv.env["DISABLE_INTERACTIVE_MODE"] = "1"

    with open(tutorial_path, "w") as fd:
        fd.write(tutorial_source_code)

    for deps in re.findall(InstallationCell.pattern, tutorial_source_code):
        venv.run(f"python -m pip install {deps}", check_rc=True, shell=True)

    venv.run(f"python {tutorial_path}", check_rc=True)


@pytest.mark.parametrize("dff_tutorial_py_file", DFF_TUTORIAL_PY_FILES)
@pytest.mark.slow
def test_tutorial_dependencies(dff_tutorial_py_file, tmp_path, virtualenv):
    with open(dff_tutorial_py_file, "r", encoding="utf-8") as fd:
        source_code = fd.read()

    check_tutorial_dependencies(
        virtualenv,
        source_code,
        tmp_path,
    )
