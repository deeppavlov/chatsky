from df_script_parser import __version__
import pytest
from pathlib import Path
from df_script_parser import py2yaml, yaml2py
from df_script_parser.dumpers_loaders import pp
from df_script_parser.processors import devnull


def test_version():
    assert __version__ == "0.1.0"


@pytest.mark.parametrize(
    "input_file,output_dir",
    [(example / "py" / "main.py", example / "py2yaml") for example in Path("examples").iterdir()],
)
def test_py2yaml(input_file, output_dir, tmp_path):
    py2yaml(input_file, tmp_path)
    for file_1, file_2 in zip(sorted(output_dir.iterdir()), sorted(tmp_path.iterdir())):
        assert sorted(file_1.open("r").readlines()) == sorted(file_2.open("r").readlines()), (
            f"Files {file_1.absolute()} and {file_2} don't match.\n"
            f"Expected file: {file_1.open('r').read()}\n"
            f"New file: {file_2.open('r').read()}"
        )


@pytest.mark.parametrize(
    "input_dir,output_file",
    [(example / "py2yaml", example / "yaml2py" / "main.py") for example in Path("examples").iterdir()],
)
def test_yaml2py(input_dir, output_file, tmp_path):
    # check pprint library
    with open(devnull, "w") as f:
        try:
            pp(1, f)
        except Exception:
            return
    yaml2py(input_dir, tmp_path / "main.py")
    file_1 = output_file
    file_2 = tmp_path / "main.py"
    assert sorted(file_1.open("r").readlines()) == sorted(file_2.open("r").readlines()), (
        f"Files {file_1.absolute()} and {file_2} don't match.\n"
        f"Expected file: {file_1.open('r').read()}\n"
        f"New file: {file_2.open('r').read()}"
    )
