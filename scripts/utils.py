from contextlib import contextmanager
import sys
from typing import Callable

from colorama import init, Fore, Style
import python_on_whales


@contextmanager
def docker_client(alternative: Callable[[], None]):
    init()
    if "linux" in sys.platform:
        docker = python_on_whales.DockerClient(compose_files=["docker-compose.yml"])
        docker.compose.up(detach=True, wait=True)
    else:
        print(f"{Fore.RED}Docker can't (shouldn't) be run on platforms other than linux!{Style.RESET_ALL}")
        alternative()
    try:
        yield docker
    finally:
        docker.compose.down(remove_orphans=False)
