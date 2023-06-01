import sys

import python_on_whales
import pytest
import dotenv

from .codestyle import lint


def _test(coverage: bool):
    test_coverage_threshold = 95

    dotenv.load_dotenv(".env_file")
    args = ["tests/"]
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
    pytest.main(args)


def test():
    return _test(coverage=True)


def test_no_cov():
    return _test(coverage=False)


def test_all():
    if "linux" in sys.platform:
        docker = python_on_whales.DockerClient(compose_files=["docker-compose.yml"])
        docker.compose.up(detach=True, wait=True)
    test()
    if "linux" in sys.platform:
        docker.compose.down(remove_orphans=False)
    lint()
