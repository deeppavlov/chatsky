import pathlib
import re
import argparse

native_type_patterns = {re.compile(r"\b(" + t + r")\["): t.capitalize() + "[" for t in ["dict", "list", "tuple"]}
cache_patterns = {re.compile(r"\bfunctools.cache\b"): "functools.lru_cache(maxsize=None)"}
fstring_patterns = {re.compile(r"\=\}"): "}"}
forwardref_patterns = {
    re.compile("from typing import ForwardRef"): "",
    re.compile(r'ForwardRef\("Context"\)'): "BaseModel",
    re.compile(r'ForwardRef\("Actor"\)'): "BaseModel",
}


def downgrade(root_dir="."):
    """
    Function that replaces patterns in the code according to the Python version in the system.
    Parameters
    ----------
    root_dir: user root directory
    """
    root_dir = pathlib.Path(root_dir)
    py_files = sum(
        [
            list(root_dir.glob(glob))
            for glob in ["*.py", "*/*.py", "*/*/*.py", "*/*/*/*.py", "*/*/*/*/*.py", "*/*/*/*/*/*.py"]
        ],
        [],
    )
    for py_file in py_files:
        text = py_file.read_text()
        # if sys.version_info < (3, 9):
        if any([i.search(text) for i in native_type_patterns.keys()]):
            text = "from typing import Dict, List, Tuple\n{}".format(text)
            for pat, replace in native_type_patterns.items():
                text = pat.sub(replace, text)
        for pat, replace in cache_patterns.items():
            text = pat.sub(replace, text)
        # if sys.version_info < (3, 8):
        for pat, replace in fstring_patterns.items():
            text = pat.sub(replace, text)
        # if sys.version_info < (3, 7):
        for pat, replace in forwardref_patterns.items():
            text = pat.sub(replace, text)
        py_file.write_text(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", help="directory", type=pathlib.Path)
    args = parser.parse_args()
    downgrade(args.directory)
