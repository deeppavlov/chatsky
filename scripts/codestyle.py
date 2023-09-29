import pathlib
from typing import List

import black
from flake8.main.cli import main as flake_main


_STANDARD_PATHS = ["dff", "scripts", "tests"]
_STANDARD_PATHS_LEN = 120
_SHORT_PATHS = ["tutorials"]
_SHORT_PATHS_LEN = 100


def _get_paths(paths: List[str]) -> List[pathlib.Path]:
    return [path for dir in paths for path in pathlib.Path(dir).glob("**/*.py")]


def lint() -> int:
    lint_result = 0
    flake8_configs = ["--select=E,W,F", "--ignore=E24,W503"]
    lint_result += flake_main([f"--max-line-length={_STANDARD_PATHS_LEN}"] + flake8_configs + _STANDARD_PATHS)
    lint_result += flake_main([f"--max-line-length={_SHORT_PATHS_LEN}"] + flake8_configs + _SHORT_PATHS)

    would_format = format(False)
    if would_format == 1:
        print(("=" * 38) + "\nBad formatting? Run: poetry run format\n" + ("=" * 38))

    # TODO: Add mypy testing
    # @mypy . --exclude venv*,build
    return lint_result or would_format


def format(modify: bool = True) -> int:
    report = black.Report(check=not modify, quiet=False)
    write = black.WriteBack.YES if modify else black.WriteBack.CHECK
    for path in _get_paths(_STANDARD_PATHS):
        mode = black.Mode(line_length=_STANDARD_PATHS_LEN)
        black.reformat_one(path, False, write, mode, report)
    for path in _get_paths(_SHORT_PATHS):
        mode = black.Mode(line_length=_SHORT_PATHS_LEN)
        black.reformat_one(path, False, write, mode, report)
    return report.return_code
