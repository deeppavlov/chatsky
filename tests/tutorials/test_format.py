import pathlib
import re

import pytest


dff_tutorials_dir = pathlib.Path(__file__).parent.parent.parent / "tutorials"
dff_tutorial_py_files = dff_tutorials_dir.glob("./**/*.py")


patterns = [
    re.compile(r"# %% \[markdown\]\n"),  # check comment block
    re.compile(r"# %%\n"),  # check python block
]

docstring_start_pattern = re.compile(r'# %% \[markdown\]\n"""\n#(?: .*:)? \d+\. .*\n(?:\n[\S\s]*)?"""(?:  # .*)?\n')
comment_start_pattern = re.compile(r'# %% \[markdown\]\n# #(?: .*:)? \d+\. .*\n#(?:\n# [\S\s]*)?')


def regexp_format_checker(dff_tutorial_py_file: pathlib.Path):
    file_lines = dff_tutorial_py_file.open("rt").readlines()
    for pattern in patterns:
        if not pattern.search("".join(file_lines)):
            raise Exception(
                f"Pattern `{pattern}` is not found in `{dff_tutorial_py_file.relative_to(dff_tutorials_dir.parent)}`."
            )
    return True


def notebook_start_checker(dff_tutorial_py_file: pathlib.Path):
    file_lines = "".join(dff_tutorial_py_file.open("rt").readlines())
    docstring_result = docstring_start_pattern.search(file_lines)
    comment_result = comment_start_pattern.search(file_lines)
    if docstring_result is not None:
        return docstring_result.pos == 0
    elif comment_result is not None:
        return comment_result.pos == 0
    else:
        raise Exception(
            (
                f"Tutorial `{dff_tutorial_py_file.relative_to(dff_tutorials_dir.parent)}` "
                + "does not have an initial markdown section. Notebook header should be prefixed "
                + "with a single '# %% [markdown]'."
            )
        )


format_checkers = [regexp_format_checker, notebook_start_checker]


@pytest.mark.parametrize("dff_tutorial_py_file", dff_tutorial_py_files)
def test_format(dff_tutorial_py_file: pathlib.Path):
    current_path = dff_tutorial_py_file.relative_to(dff_tutorials_dir.parent)
    for checker in format_checkers:
        assert checker(dff_tutorial_py_file), f"Tutorial {current_path} didn't pass formatting checks!"
