import pathlib
import re

import pytest


dff_examples_dir = pathlib.Path(__file__).parent.parent.parent / "examples"
dff_example_py_files = dff_examples_dir.glob("./**/*.py")


patterns = [
    re.compile("# pip install dff.*# Uncomment this line"),  # check dff installation
    re.compile("# %% [markdown]\n"),  # check comment block
    re.compile("# %%\n"),  # check python block
]


def regexp_format_checker(dff_example_py_file: pathlib.Path):
    file_lines = dff_example_py_file.open("rt").readlines()
    text = "\n".join(file_lines)
    for pattern in patterns:
        if not pattern.search(text):
            raise Exception(
                f"Pattern `{pattern}` is not found in `{dff_example_py_file.relative_to(dff_examples_dir.parent)}`."
            )
    return True


format_checkers = [regexp_format_checker]


@pytest.mark.parametrize("dff_example_py_file", dff_example_py_files)
def test_format(dff_example_py_file: pathlib.Path):
    for checker in format_checkers:
        checker(dff_example_py_file)
