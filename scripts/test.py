import sys
from typing import Optional
import pytest
import dotenv
from python_on_whales import DockerClient

from .codestyle import lint
from .utils import docker_client


def _test(coverage: bool, dependencies: bool) -> int:
    """
    Run framework tests, located in `tests/` dir, using env defined in `.env_file`.
    Please keep in mind that:

    1. Skipping `telegram` tests is **always** allowed.
    2. Enabling dependencies is effectively same as enabling docker
        (docker containers **should** be running in that case).
    3. Coverage requires all dependencies and docker (will have no effect otherwise).
    """
    test_coverage_threshold = 95

    dotenv.load_dotenv(".env_file")
    args = ["tests/"]

    if dependencies and coverage:
        args = [
            "-m",
            "not no_coverage",
            "--allow-skip=telegram",
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


@docker_client
def test_no_cov(docker: Optional[DockerClient]) -> int:
    result = _test(False, docker is not None)
    return result or lint()


@docker_client
def test_no_deps(_: Optional[DockerClient]) -> int:
    return _test(False, False)


@docker_client
def test_all(docker: Optional[DockerClient]) -> int:
    result = _test(True, docker is not None)
    return result or lint()
