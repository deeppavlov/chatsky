import os
from pathlib import Path
import shutil
from typing import Optional

import dotenv
import scripts.patch_sphinx  # noqa: F401
import sphinx.ext.apidoc as apidoc
import sphinx.cmd.build as build
from colorama import init, Fore, Style
from python_on_whales import DockerClient

from .utils import docker_client
from .clean import clean_docs

from sphinx_polyversion.main import main as poly_main


def _build_drawio(docker: DockerClient):
    if len(docker.image.list("rlespinasse/drawio-export")) == 0:
        docker.image.pull("rlespinasse/drawio-export", quiet=True)
    docker.container.run(
        "rlespinasse/drawio-export",
        ["-f", "png", "--remove-page-suffix"],
        remove=True,
        name="drawio-convert",
        volumes=[(f"{os.getcwd()}/docs/source/drawio_src", "/data", "rw")],
    )
    docker.container.run(
        "rlespinasse/drawio-export",
        ["-R", f"{os.geteuid()}:{os.getegid()}", "/data"],
        entrypoint="chown",
        remove=True,
        name="drawio-chown",
        volumes=[(f"{os.getcwd()}/docs/source/drawio_src", "/data", "rw")],
    )

    drawio_root = Path("docs/source/drawio_src/")
    destination = Path("docs/source/_static/drawio/")
    destination.mkdir(parents=True, exist_ok=True)
    for path in drawio_root.glob("./**/export"):
        target = destination / path.relative_to(drawio_root).parent
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(path, target, dirs_exist_ok=True)
        print(f"Drawio images built from {path.parent} to {target}")


@docker_client
def docs(docker: Optional[DockerClient]):
    init()
    if docker is not None:
        clean_docs()
        dotenv.load_dotenv(".env_file")
        os.environ["DISABLE_INTERACTIVE_MODE"] = "1"
        _build_drawio(docker)
        result = apidoc.main(["-e", "-E", "-f", "-o", "docs/source/apiref", "dff"])
        result += build.make_main(["-M", "clean", "docs/source", "docs/build"])
        poly_path = "docs/source/poly.py"
        poly_main([poly_path, poly_path])
        """Possible TO-DO: Add version dependent poly.py pathfile variable. Maybe in a separate file?"""
        exit(result)
    else:
        print(f"{Fore.RED}Docs can be built on Linux platform only!{Style.RESET_ALL}")
        exit(1)
