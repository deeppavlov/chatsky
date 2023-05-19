import pathlib
from typing import List

import black
from flake8.api import legacy as flake8


_STANDARD_PATHS = ["dff", "examples", "scripts", "tests"]
_STANDARD_PATHS_LEN = 120
_SHORT_PATHS = ["tutorials"]
_SHORT_PATHS_LEN = 100


def _get_paths(paths: List[str]) -> List[pathlib.Path]:
    return [path for dir in paths for path in pathlib.Path(dir).glob("**/*.py")]


def _lint_result(selector: List[str], report: flake8.Report) -> int:
    return sum(len(report.get_statistics(sel)) for sel in selector)


def lint() -> int:
    lint_result = 0
    selector = ["E", "W", "F"]
    standard_style_guide = flake8.get_style_guide(select=selector, max_line_length=_STANDARD_PATHS_LEN)
    lint_result += _lint_result(selector, standard_style_guide.check_files(_STANDARD_PATHS))
    short_style_guide = flake8.get_style_guide(select=selector, max_line_length=_SHORT_PATHS_LEN)
    lint_result += _lint_result(selector, short_style_guide.check_files(_SHORT_PATHS))

    would_format = format(False)
    if would_format == 1:
        print("================================\nBad formatting? Run: make format\n================================")
    return lint_result or would_format



def format(modify: bool = True) -> int:
    report = black.Report(check=not modify, quiet=False)
    write = black.WriteBack.YES if modify else black.WriteBack.CHECK
    for path in _get_paths(_STANDARD_PATHS):
        mode = black.FileMode(line_length=_STANDARD_PATHS_LEN)
        black.reformat_one(path, False, write, mode, report)
    for path in _get_paths(_SHORT_PATHS):
        mode = black.FileMode(line_length=_SHORT_PATHS_LEN)
        black.reformat_one(path, False, write, mode, report)
    return report.return_code
