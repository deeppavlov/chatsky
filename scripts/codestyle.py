import pathlib
from typing import List

import black
from flake8.main.cli import main as flake_main


_STANDARD_PATHS = ["dff", "scripts", "tests", ".github", "docs/source/utils", "utils"]
_STANDARD_PATHS_LEN = 120
_SHORT_PATHS = ["tutorials"]
_SHORT_PATHS_LEN = 80


def _get_paths(paths: List[str]) -> List[pathlib.Path]:
    return [path for dir in paths for path in pathlib.Path(dir).glob("**/*.py")]


def _run_flake():
    lint_result = 0
    flake8_configs = [
        "--select=E,W,F",
        # black formats binary operators after line breaks
        "--ignore=W503",
        "--per-file-ignores="
        # allow imports in init files without use
        "**/__init__.py:F401 "
        # patches that execute code before imports
        "**3_load_testing_with_locust.py:E402 **4_streamlit_chat.py:E402",
    ]
    lint_result += flake_main([f"--max-line-length={_STANDARD_PATHS_LEN}"] + flake8_configs + _STANDARD_PATHS)
    lint_result += flake_main([f"--max-line-length={_SHORT_PATHS_LEN}"] + flake8_configs + _SHORT_PATHS)

    exit(lint_result)


def _run_black(modify: bool):
    report = black.Report(check=not modify, quiet=False)
    write = black.WriteBack.YES if modify else black.WriteBack.CHECK
    for path in _get_paths(_STANDARD_PATHS):
        mode = black.Mode(line_length=_STANDARD_PATHS_LEN)
        black.reformat_one(path, False, write, mode, report)
    for path in _get_paths(_SHORT_PATHS):
        mode = black.Mode(line_length=_SHORT_PATHS_LEN)
        black.reformat_one(path, False, write, mode, report)
    exit(report.return_code)
