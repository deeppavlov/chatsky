import sys
from typing import Optional
import pytest
import dotenv
from python_on_whales import DockerClient

from .utils import docker_client


def _test(coverage: bool = False, dependencies: bool = False, quick: bool = False) -> int:
    """
    Run framework tests, located in `tests/` dir, using env defined in `.env_file`.
    Please keep in mind that:

    1. Enabling dependencies is effectively same as enabling docker
        (docker containers **should** be running in that case).
    2. Coverage requires all dependencies and docker (will have no effect otherwise).

    :param coverage: Enable coverage calculation
    :param dependencies: Disallow skipping tests
    :param quick: Deselect 'slow' and 'docker' marked tests
    """
    test_coverage_threshold = 90

    dotenv.load_dotenv(".env_file")
    args = ["tests/"]

    if quick:
        args = [
            "-m",
            "not docker",
            "-m",
            "not slow",
            *args,
        ]

    if dependencies and coverage:
        args = [
            "-m",
            "not no_coverage",
            *args,
        ]
    elif dependencies:
        args = [
            "--allow-skip=docker",
            *args,
        ]
    else:
        args = [
            "--allow-skip=all",
            *args,
        ]

    if "linux" not in sys.platform:
        args = [
            "-m",
            "not docker",
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

    return pytest.main(args)


def quick_test():
    exit(_test(quick=True))


def quick_test_coverage():
    exit(_test(coverage=True, quick=True))


@docker_client
def test_no_cov(docker: Optional[DockerClient]):
    result = _test(False, docker is not None)
    exit(result)


@docker_client
def test_no_deps(_: Optional[DockerClient]):
    exit(_test(False, False))


@docker_client
def test_all(docker: Optional[DockerClient]):
    result = _test(True, docker is not None)
    exit(result)
