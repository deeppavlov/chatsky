import os

import dotenv
import scripts.patch_sphinx  # noqa: F401
import sphinx.ext.apidoc as apidoc
import sphinx.cmd.build as build
from colorama import init, Fore, Style

from .utils import docker_client
from .clean import clean_docs


def docs():
    init()
    with docker_client() as docker:
        if docker is not None:
            clean_docs()
            dotenv.load_dotenv(".env_file")
            os.environ["DISABLE_INTERACTIVE_MODE"] = "1"
            apidoc.main(["-e", "-E", "-f", "-o", "docs/source/apiref", "dff"])
            build.make_main(["-M", "clean", "docs/source", "docs/build"])
            build.build_main(["-b", "html", "-W", "--keep-going", "docs/source", "docs/build"])
        else:
            print(f"{Fore.RED}Docs can be built on Linux platform only!{Style.RESET_ALL}")
            exit(1)
