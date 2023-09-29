import sys
from typing import Callable, Optional

from python_on_whales import DockerClient
from wrapt import decorator


@decorator
def docker_client(wrapped: Callable[[Optional[DockerClient]], None], _, __, ___):
    if "linux" in sys.platform:
        docker = DockerClient(compose_files=["docker-compose.yml"])
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
