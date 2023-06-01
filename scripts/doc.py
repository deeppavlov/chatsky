import os

import dotenv
import scripts.patch_sphinx  # noqa: F401
import sphinx.ext.apidoc as apidoc
import sphinx.cmd.build as build

from .clean import clean_docs


def docs():
    clean_docs()
    dotenv.load_dotenv(".env_file")
    os.environ["DISABLE_INTERACTIVE_MODE"] = "1"
    apidoc.main(["-e", "-E", "-f", "-o", "docs/source/apiref", "dff"])
    build.make_main(["-M", "clean", "docs/source", "docs/build"])
    build.build_main(["-b", "html", "-W", "--keep-going", "docs/source", "docs/build"])
