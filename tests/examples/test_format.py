import pathlib
import re

import pytest


dff_examples_dir = pathlib.Path(__file__).parent.parent.parent / "examples"
dff_example_py_files = dff_examples_dir.glob("./**/*.py")


patterns = [
    re.compile(r"# %% \[markdown\]\n"),  # check comment block
    re.compile(r"# %%\n"),  # check python block
]

start_pattern = re.compile(r'# %% \[markdown\]\n"""\n# \d+\. .*\n\n(?:[\S\s]*\n)?"""\n')


def regexp_format_checker(dff_example_py_file: pathlib.Path):
    file_lines = dff_example_py_file.open("rt").readlines()
    for pattern in patterns:
        if not pattern.search("".join(file_lines)):
            raise Exception(
                f"Pattern `{pattern}` is not found in `{dff_example_py_file.relative_to(dff_examples_dir.parent)}`."
            )
    return True


def notebook_start_checker(dff_example_py_file: pathlib.Path):
    file_lines = dff_example_py_file.open("rt").readlines()
    result = start_pattern.search("".join(file_lines))
    if result is None:
        raise Exception(
            f"Example `{dff_example_py_file.relative_to(dff_examples_dir.parent)}` doesn't start as a notebook."
        )
    else:
        return result.pos == 0


format_checkers = [regexp_format_checker, notebook_start_checker]


@pytest.mark.parametrize("dff_example_py_file", dff_example_py_files)
def test_format(dff_example_py_file: pathlib.Path):
    current_path = dff_example_py_file.relative_to(dff_examples_dir.parent)
    for checker in format_checkers:
        assert checker(dff_example_py_file), f"Example {current_path} didn't pass example checks!"
