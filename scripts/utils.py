import sys
from typing import Any, Callable, Optional

from python_on_whales import DockerClient
from wrapt import decorator


_DockerClientWrapperType = Callable[[Optional[DockerClient]], int]


def docker_client(run_on_linux_only: bool = True) -> Callable[[_DockerClientWrapperType, Any, Any, Any], int]:
    @decorator
    def wrapper(wrapped: _DockerClientWrapperType, _, __, ___) -> int:
        if "linux" in sys.platform or not run_on_linux_only:
            docker = DockerClient(
                compose_files=["docker-compose.yml"],
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
