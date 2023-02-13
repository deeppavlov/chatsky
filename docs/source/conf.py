import os
import sys
import re

from dff_sphinx_theme.extras import generate_example_links_for_notebook_creation, regenerate_apiref

# -- Path setup --------------------------------------------------------------

sys.path.append(os.path.abspath("."))
from utils.notebook import insert_installation_cell_into_py_example  # noqa: E402

# -- Project information -----------------------------------------------------

project = "DFF"
copyright = "2023, DeepPavlov"
author = "DeepPavlov"

# The full version, including alpha/beta/rc tags
release = "0.2.0"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.extlinks",
    "sphinxcontrib.katex",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
    "nbsphinx",
    "sphinx_gallery.load_style",
    "IPython.sphinxext.ipython_console_highlighting",
]

suppress_warnings = ["image.nonlocal_uri"]
source_suffix = ".rst"
master_doc = "index"

version = re.match(r"^\d\.\d.\d", release).group()
language = "en"

pygments_style = "default"

add_module_names = False


# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["*.py", "utils/*.py", "**/_*.py"]

html_short_title = "None"

# -- Options for HTML output -------------------------------------------------

sphinx_gallery_conf = {
    "promote_jupyter_magic": True,
}

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "pydata_sphinx_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

html_show_sourcelink = False


# Finding examples directories
nbsphinx_custom_formats = {".py": insert_installation_cell_into_py_example()}
nbsphinx_prolog = """
:tutorial_name: {{ env.docname }}
:tutorial_path: \\.
:github_url: deeppavlov/dialog_flow_framework
"""

html_context = {
    "github_user": "deeppavlov",
    "github_repo": "dialog_flow_framework",
    "github_version": "dev",
    "doc_path": "docs/source",
}

# Theme options
html_theme_options = {
    "use_edit_page_button": True,
    "icon_links": [
        {
            "name": "Deeppavlov Forum",
            "url": "https://forum.deeppavlov.ai",
            "icon": "https://static.tildacdn.com/tild6538-3537-4239-b632-623238366335/_DeepPavlov_200x200-.svg",
            "type": "url",
        },
        {
            "name": "Telegram",
            "url": "https://t.me/DeepPavlovDreamDiscussions",
            "icon": "fa-brands fa-telegram",
            "type": "fontawesome",
        },
        {
            "name": "GitHub",
            "url": "https://github.com/deeppavlov/dialog_flow_framework",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
    ],
}


autodoc_default_options = {"members": True, "undoc-members": False, "private-members": False}


def setup(_):
    generate_example_links_for_notebook_creation(
        [
            "examples/script/*.py",
            "examples/pipeline/[1]*.py",
            "examples/context_storages/[1]*.py",
            "examples/messengers/*.py",
        ]
    )
    regenerate_apiref(
        [
            ("dff.context_storages", "Context Storages"),
            ("dff.messengers", "Messenger Interfaces"),
            ("dff.pipeline", "Pipeline"),
            ("dff.script", "Script"),
        ]
    )
