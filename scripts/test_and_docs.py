import os
import sys

import scripts.patch_sphinx  # noqa: F401
import sphinx.ext.apidoc as apidoc
import sphinx.cmd.build as build
import python_on_whales
import pytest
import dotenv

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
    if "linux" in sys.platform:
        docker = python_on_whales.DockerClient(compose_files=["docker-compose.yml"])
        docker.compose.up(detach=True, wait=True)
    test()
    if "linux" in sys.platform:
        docker.compose.down(remove_orphans=False)
    lint()


def docs():
    clean_docs()
    dotenv.load_dotenv(".env_file")
    os.environ["DISABLE_INTERACTIVE_MODE"] = "1"
    apidoc.main(["-e", "-E", "-f", "-o", "docs/source/apiref", "dff"])
    build.make_main(["-M", "clean", "docs/source", "docs/build"])
    build.build_main(["-b", "html", "-W", "--keep-going", "docs/source", "docs/build"])
