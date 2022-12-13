import os
import sys

from dff_sphinx_theme.extras import generate_example_links_for_notebook_creation, regenerate_apiref

# -- Path setup --------------------------------------------------------------

sys.path.append(os.path.abspath("."))
from utils.notebook import add_installation_cell_into_py  # noqa: E402

# -- Project information -----------------------------------------------------

project = "Dialog Flow Framework"
copyright = "2021, Denis Kuznetsov"
author = "Denis Kuznetsov"

# The full version, including alpha/beta/rc tags
release = "0.10.1"


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

version = "0.10.1"
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
html_theme = "dff_sphinx_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

html_show_sourcelink = False


# Finding examples directories
nbsphinx_custom_formats = {".py": add_installation_cell_into_py}
nbsphinx_prolog = """
:tutorial_name: {{ env.docname }}
:tutorial_path: \\.
:github_url: deeppavlov/dialog_flow_framework
"""

# Theme options
html_theme_options = {
    "logo_only": True,
    "tab_intro_dff": "#",
    "tab_intro_addons": "#",
    "tab_intro_designer": "#",
    "tab_get_started": "#",
    "tab_tutorials": "#",
    # Matches ROOT tag, should be ONE PER MODULE, other tabs = other modules (may be relative paths)
    "tab_documentation": "./",
    "tab_ecosystem": "#",
    "tab_about_us": "#",
}


def setup(_):
    generate_example_links_for_notebook_creation(
        [
            "examples/engine/*.py",
            "examples/pipeline/*.py",
            "examples/db_connector/*.py",
            "examples/generics/*.py",
        ]
    )
    regenerate_apiref(
        [
            ("dff.connectors.db", "db_connectors"),
            ("dff.connectors.messenger", "messenger_interfaces"),
            ("dff.core.engine", "engine"),
            ("dff.core.pipeline", "pipeline"),
        ]
    )
