import sys
from typing import Callable, Optional

from python_on_whales import DockerClient
from wrapt import decorator


@decorator
def docker_client(wrapped: Callable[[Optional[DockerClient]], None], _, __, ___):
    if "linux" in sys.platform:
        docker = DockerClient(compose_files=["docker-compose.yml"])
        docker.compose.up(detach=True, wait=True)
        result = wrapped(docker)
        docker.compose.down(remove_orphans=False)
    else:
        result = wrapped(None)
    return result
