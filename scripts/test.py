from typing import Optional
import pytest
import dotenv
from python_on_whales import DockerClient

from .utils import docker_client


def _test(coverage: bool = False, no_skip: bool = False, quick: bool = False, use_docker: bool = False) -> int:
    """
    Run framework tests, located in `tests/` dir, using env defined in `.env_file`.
    Please keep in mind that:

    1. Enabling dependencies is effectively same as enabling docker
        (docker containers **should** be running in that case).
    2. Coverage requires all dependencies and docker (will have no effect otherwise).

    :param coverage: Enable coverage calculation
    :param no_skip: Disallow skipping tests
    :param quick: Deselect 'slow' and 'docker' marked tests
    :param use_docker: Enable tests marked as 'docker'
    """
    test_coverage_threshold = 90

    dotenv.load_dotenv(".env_file")
    args = ["tests/"]

    if coverage:
        args = [
            f"--cov-fail-under={test_coverage_threshold}",
            "--cov-report",
            "html",
            "--cov-report",
            "term",
            "--cov=chatsky",
            "-m",
            "not no_coverage",
            *args,
        ]
    if no_skip and use_docker:
        None
    if no_skip and not use_docker:
        args = [
            "--allow-skip=docker",
            *args,
        ]
    if not no_skip:
        args = [
            "--allow-skip=all",
            *args,
        ]
    if quick:
        args = [
            "-m",
            "not docker",
            "-m",
            "not slow",
            *args,
        ]
    if quick and use_docker:
        raise ValueError()
    with docker_client(use_docker):
        return pytest.main(args)


def run_tests(quick, coverage, no_skip, use_docker):
    result = _test(coverage=coverage, no_skip=no_skip, quick=quick, use_docker=use_docker)
    exit(result)
