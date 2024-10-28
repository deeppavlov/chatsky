import sys
from typing import Callable, Optional

from python_on_whales import DockerClient


def docker_client(wrapped: Callable[[Optional[DockerClient]], int]):
    def wrapper() -> int:
        if "linux" in sys.platform:
            docker = DockerClient(
                compose_files=["compose.yml"],
                compose_profiles=["context_storage", "stats"],
            )
            docker.compose.up(detach=True, wait=True, quiet=True)
            error = None
            try:
                result = wrapped(docker)
            except Exception as e:
                result = 1
                error = e
            finally:
                docker.compose.down(remove_orphans=False, quiet=True)
            if error is not None:
                raise error
        else:
            result = wrapped(None)
        return result
    return wrapper
