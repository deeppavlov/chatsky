import os

import python_on_whales
import pytest
import dotenv

import docs.source.utils.patching as patching
from .codestyle import lint
from .clean import clean_docs


def test():
    test_coverage_threshold = 95
    test_coverage_report = "html"
    test_coverage_term = "term"
    test_coverage = "dff"

    dotenv.load_dotenv(".env_file")
    pytest.main(
        [
            f"--cov-fail-under={test_coverage_threshold}",
            "--cov-report",
            test_coverage_report,
            "--cov-report",
            test_coverage_term,
            f"--cov={test_coverage}",
            "tests/",
        ]
    )


def test_all():
    docker = python_on_whales.DockerClient(compose_files=["docker-compose.yml"])
    docker.compose.up(detach=True, wait=True)
    test()
    docker.compose.down(remove_orphans=False)
    lint()


def docs():
    clean_docs()
    patching.main()
    # Sphinx apidoc
    # Sphinx clean
    dotenv.load_dotenv(".env_file")
    os.environ["DISABLE_INTERACTIVE_MODE"] = 1
    # Sphinx build
