import os
import sys
import re
import importlib.metadata
import pydata_sphinx_theme

# -- Path setup --------------------------------------------------------------

sys.path.append(os.path.abspath("."))
from utils.notebook import py_percent_to_notebook  # noqa: E402
from utils.generate_tutorials import generate_tutorial_links_for_notebook_creation  # noqa: E402
from utils.link_misc_files import link_misc_files  # noqa: E402
from utils.regenerate_apiref import regenerate_apiref  # noqa: E402
from sphinx_polyversion import load
from sphinx_polyversion.git import GitRef

# -- Project information -----------------------------------------------------

data = load(globals())  # adds variables `current` and `revisions`
current: GitRef = data['current']
print("current is: ", current)
print("current[0] is: ", current[0])

_distribution_metadata = importlib.metadata.metadata('dff')

project = _distribution_metadata["Name"]
copyright = "2023, DeepPavlov"
author = "DeepPavlov"
release = _distribution_metadata["Version"]


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

# Finding tutorials directories
nbsphinx_custom_formats = {".py": py_percent_to_notebook}
nbsphinx_prolog = """
:tutorial_name: {{ env.docname }}
"""

html_logo = "_static/images/logo-simple.svg"

nbsphinx_thumbnails = {
    "tutorials/*": "_static/images/logo-simple.svg",
}

html_context = {
    "github_user": "deeppavlov",
    "github_repo": "dialog_flow_framework",
    "github_version": "master",
    "doc_path": "docs/source",
}

html_css_files = [
    "css/custom.css",
]


json_url = "https://raw.githubusercontent.com/ZergLev/dialog_flow_framework/master/docs/source/_static/switcher.json"

# Theme options
html_theme_options = {
    "header_links_before_dropdown": 5,
    "logo": {
        "alt_text": "DFF logo (simple and nice)",
        "text": "Dialog Flow Framework",
    },
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
            "url": "https://github.com/deeppavlov/dialog_flow_framework",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
    ],
    "secondary_sidebar_items": ["page-toc", "source-links", "example-links"],
    "switcher": {
        "json_url": json_url,
        # "version_match" : version,
        "version_match": current[0],
    },
    "navbar_start": ["navbar-logo", "version-switcher"],
}

favicons = [
    {"href": "images/logo-dff.svg"},
]


autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "private-members": True,
    "member-order": "bysource",
    "exclude-members": "_abc_impl, model_fields",
}


def setup(_):
    link_misc_files(
        [
            "utils/db_benchmark/benchmark_schema.json",
            "utils/db_benchmark/benchmark_streamlit.py",
        ]
    )
    generate_tutorial_links_for_notebook_creation(
        [
            ("tutorials.context_storages", "Context Storages"),
            (
                "tutorials.messengers",
                "Interfaces",
                [
                    ("telegram", "Telegram"),
                    ("web_api_interface", "Web API"),
                ],
            ),
            ("tutorials.pipeline", "Pipeline"),
            (
                "tutorials.script",
                "Script",
                [
                    ("core", "Core"),
                    ("responses", "Responses"),
                ],
            ),
            ("tutorials.utils", "Utils"),
            ("tutorials.stats", "Stats"),
        ]
    )
    regenerate_apiref(
        [
            ("dff.context_storages", "Context Storages"),
            ("dff.messengers", "Messenger Interfaces"),
            ("dff.pipeline", "Pipeline"),
            ("dff.script", "Script"),
            ("dff.stats", "Stats"),
            ("dff.utils.testing", "Testing Utils"),
            ("dff.utils.turn_caching", "Caching"),
            ("dff.utils.db_benchmark", "DB Benchmark"),
        ]
    )
