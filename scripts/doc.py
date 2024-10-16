import os
import sys
from pathlib import Path
import shutil
from typing import Optional

import dotenv
import scripts.patch_sphinx  # noqa: F401
import sphinx.ext.apidoc as apidoc
import sphinx.cmd.build as build
from colorama import init, Fore, Style
from python_on_whales import DockerClient

from .clean import clean_docs
from .utils import docker_client

from sphinx_polyversion.main import main as poly_main


def _build_drawio(root_dir: str = "."):
    drawio_root = root_dir + "/docs/source/drawio_src"
    destination = root_dir + "/docs/source/_static/drawio"
    docker = DockerClient(
        compose_files=[f"{root_dir}/compose.yml"],
        compose_profiles=["context_storage", "stats"],
    )
    if len(docker.image.list("rlespinasse/drawio-export")) == 0:
        docker.image.pull("rlespinasse/drawio-export", quiet=True)
    docker.container.run(
        "rlespinasse/drawio-export",
        ["-f", "png", "--remove-page-suffix"],
        remove=True,
        name="drawio-convert",
        volumes=[(drawio_root, "/data", "rw")],
    )
    docker.container.run(
        "rlespinasse/drawio-export",
        ["-R", f"{os.geteuid()}:{os.getegid()}", "/data"],
        entrypoint="chown",
        remove=True,
        name="drawio-chown",
        volumes=[(drawio_root, "/data", "rw")],
    )

    drawio_root = Path(drawio_root)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for path in drawio_root.glob("./**/export"):
        target = destination / path.relative_to(drawio_root).parent
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(path, target, dirs_exist_ok=True)
        print(f"Drawio images built from {path.parent} to {target}")


def docs():
    init()
    clean_docs()
    dotenv.load_dotenv(".env_file")
    os.environ["DISABLE_INTERACTIVE_MODE"] = "1"
    # polyversion_build is False for local builds and PR builds.
    # In other words, it's only 'True' when docs are to be deployed on gh-pages
    polyversion_build = os.getenv("POLYVERSION_BUILD", default="False")
    if polyversion_build == "True":
        poly_path = "docs/source/poly.py"
        sys.argv = [poly_path, poly_path]
        poly_main()
        exit(0)
    else:
        result = apidoc.main(["-e", "-E", "-f", "-o", "docs/source/apiref", "chatsky"])
        result += build.make_main(["-M", "clean", "docs/source", "docs/build"])
        result += build.build_main(["-b", "html", "-W", "--keep-going", "docs/source", "docs/build"])
        exit(result)


# Functions to be called from ChatskySphinxBuilder before build
def pre_sphinx_build_funcs(root_dir: str):
    _build_drawio(root_dir)
    apiref_dir = root_dir + "/docs/source/apiref"
    apidoc.main(["-e", "-E", "-f", "-o", apiref_dir, "chatsky"])
