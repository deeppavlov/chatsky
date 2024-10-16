import os
import sys
from typing import Callable, Optional

from python_on_whales import DockerClient
from wrapt import decorator


@decorator
def docker_client(wrapped: Callable[[Optional[DockerClient]], int], _, __, ___) -> int:
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


# Making GitHub links version dependent in tutorials and API reference (Pull Requests and local builds)
# Local builds will have the right links, but there's no multi-versioning for them
def set_up_example_and_source_links(source_dir: str):
    branch_name = os.getenv("BRANCH_NAME", default="")
    if branch_name is not "":
        branch_name = branch_name + "/"

    example_links_file = source_dir + "_templates/example-links.html"
    source_links_file = source_dir + "_templates/source-links.html"
    for links_file in [example_links_file, source_links_file]:
        with open(links_file, "r") as file:
            contents = file.read()
            contents = contents.replace('DOC_VERSION', branch_name)

        with open(links_file, "w") as file:
            file.write(contents)
