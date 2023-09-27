import sys
import pytest
import dotenv

from .codestyle import lint
from .utils import docker_client


def _test(coverage: bool, dependencies: bool):
    test_coverage_threshold = 95

    dotenv.load_dotenv(".env_file")
    args = ["tests/"]

    if dependencies and coverage:
        args = [
            "--allow-skip=telegram",
            "-m \"not no_coverage\"",
            *args,
        ]
    elif dependencies:
        args = [
            "--allow-skip=telegram,docker",
            *args,
        ]
    else:
        args = [
            "--allow-skip=all",
            *args,
        ]

    if "linux" not in sys.platform:
        args = [
            '-m "not docker"',
            *args,
        ]
    if coverage:
        args = [
            f"--cov-fail-under={test_coverage_threshold}",
            "--cov-report",
            "html",
            "--cov-report",
            "term",
            "--cov=dff",
            *args,
        ]
    else:
        args = [
            "--tb=long",
            "-vv",
            "--cache-clear",
            *args,
        ]

    pytest.main(args)


def test_no_cov():
    return _test(coverage=False, dependencies=True)


def test_no_deps():
    return _test(coverage=False, dependencies=False)


def test_all():
    with docker_client() as _:
        _test(coverage=True, dependencies=True)
    lint()
