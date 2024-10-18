import os
import sys
from pathlib import Path
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
def set_up_source_links(source_dir: str):
    branch_name = os.getenv("BRANCH_NAME", default="")
    if branch_name != "":
        branch_name = branch_name + "/"

    apiref_source = Path(source_dir) / "/apiref"
    for doc_file in iter(apiref_source.glob("./*.rst")):
        with open(doc_file, "r+") as file:
            contents = file.read()
            doc_file.write_text(f":doc_version: {branch_name}\n{contents}")
