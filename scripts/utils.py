from contextlib import contextmanager
import sys

import python_on_whales


@contextmanager
def docker_client():
    if "linux" in sys.platform:
        docker = python_on_whales.DockerClient(compose_files=["docker-compose.yml"])
        docker.compose.up(detach=True, wait=True)
        try:
            yield docker
        finally:
            docker.compose.down(remove_orphans=False)
    else:
        yield None
