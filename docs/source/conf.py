import os
import sys
import re
import git
import importlib.metadata

# -- Path setup --------------------------------------------------------------

sys.path.append(os.path.abspath("."))
from utils.notebook import py_percent_to_notebook  # noqa: E402

# -- Project information -----------------------------------------------------

_distribution_metadata = importlib.metadata.metadata('chatsky')

project = _distribution_metadata["Name"]
copyright = "2022 - 2025, DeepPavlov"
author = "DeepPavlov"
release = _distribution_metadata["Version"]

current_commit = git.Repo('../../').head.commit
today = current_commit.committed_datetime
today = today.strftime("%b %d, %Y")

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinx.ext.extlinks",
    "sphinxcontrib.katex",
    "sphinx_copybutton",
    "sphinx_favicon",
    "sphinx_autodoc_typehints",
    "nbsphinx",
    "sphinx_gallery.load_style",
    "IPython.sphinxext.ipython_console_highlighting",
]

suppress_warnings = ["image.nonlocal_uri", "config.cache"]
nbsphinx_allow_errors = os.getenv("NBSPHINX_ALLOW_ERRORS", "false").lower() in ("true", "1")
source_suffix = ".rst"
master_doc = "index"

version = re.match(r"^\d\.\d", release).group()
language = "en"

pygments_style = "default"

add_module_names = False


# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["*.py", "utils/*.py", "**/_*.py", "_misc/*.py"]

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
html_static_path = ["_static"]

html_show_sourcelink = False

autosummary_generate_overwrite = False

doc_version = os.getenv("DOC_VERSION", default="master")
if doc_version != "":
    doc_version = doc_version + '/'
# Finding tutorials directories
nbsphinx_custom_formats = {".py": py_percent_to_notebook}
nbsphinx_prolog = f"""
:tutorial_name: {{{{ env.docname }}}}
:doc_version: {doc_version}
"""

extlinks = {
    'github_source_link': (f"https://github.com/deeppavlov/chatsky/blob/{doc_version}%s", None),
}

html_logo = "_static/images/Chatsky-full-dark.svg"

nbsphinx_thumbnails = {
    "tutorials/*": "_static/images/Chatsky-min-light.svg",
}

html_context = {
    "github_user": "deeppavlov",
    "github_repo": "chatsky",
    "github_version": "master",
    "doc_path": "docs/source",
}

html_css_files = [
    "css/custom.css",
]

# Version switcher data
version_data = os.getenv("DOC_VERSION", default="master")
switcher_url = "https://deeppavlov.github.io/chatsky/switcher.json"

# Theme options
html_theme_options = {
    "header_links_before_dropdown": 5,
    "icon_links": [
        {
            "name": "DeepPavlov Forum",
            "url": "https://forum.deeppavlov.ai",
            "icon": "_static/images/logo-deeppavlov.svg",
            "type": "local",
        },
        {
            "name": "Telegram",
            "url": "https://t.me/DeepPavlovDreamDiscussions",
            "icon": "fa-brands fa-telegram",
            "type": "fontawesome",
        },
        {
            "name": "GitHub",
            "url": "https://github.com/deeppavlov/chatsky",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
    ],
    "secondary_sidebar_items": ["page-toc", "source-links", "example-links"],
    "switcher": {
        "json_url": switcher_url,
        "version_match": version_data,
    },
    "navbar_persistent": ["search-button.html", "theme-switcher.html"],
    "navbar_end": ["version-switcher.html", "navbar-icon-links.html"],
}


favicons = [
    {"href": "images/Chatsky-min-light.svg"},
]


autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "private-members": True,
    "special-members": "__call__",
    "member-order": "bysource",
    "exclude-members": "_abc_impl, model_fields, model_computed_fields, model_config",
}


def setup(_):
    from setup import setup
    setup()
