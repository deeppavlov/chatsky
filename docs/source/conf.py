# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys

from jupytext import jupytext

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

sys.path.append(os.path.abspath("."))
from generate_notebook_links import generate_links


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
    "sphinx_gallery.load_style"
]

suppress_warnings = ["image.nonlocal_uri"]
source_suffix = ".rst"
master_doc = "index"

version = "0.10.1"
language = "en"

pygments_style = "default"


# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["*.py", "**/_*"]

html_short_title = "None"

# -- Options for HTML output -------------------------------------------------

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
nbsphinx_custom_formats = {
    '.py': lambda s: jupytext.reads(s, 'py:percent')
}


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
    generate_links(include=["examples/pipeline/1*.py", "examples/pipeline/_*.py"])
