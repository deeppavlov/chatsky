from python_on_whales import DockerClient
from contextlib import contextmanager


@contextmanager
def docker_client(use_docker: bool):
    if use_docker:
        docker_client = DockerClient(
            compose_files=["compose.yml"],
            compose_profiles=["context_storage", "stats"],
        )
        docker_client.compose.up(detach=True, wait=True, quiet=True)
        try:
            yield docker_client
        finally:
            docker_client.compose.down(remove_orphans=False, quiet=True)
    else:
        yield None
