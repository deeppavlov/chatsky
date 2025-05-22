import sys
from typing import Callable, Optional

from python_on_whales import DockerClient
from contextlib import contextmanager

@contextmanager
def docker_client(use_docker: bool):
    if use_docker:
        docker = DockerClient(
            compose_files=["compose.yml"],
            compose_profiles=["context_storage", "stats"],
        )
        docker.compose.up(detach=True, wait=True, quiet=True)
        try:
            yield docker
        finally:
            docker.compose.down(remove_orphans=False, quiet=True)
    else:
        yield None
