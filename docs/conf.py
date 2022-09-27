import glob
import re
import shutil
import sys
import os

from sphinx_gallery.sorting import FileNameSortKey

sys.path.append(os.path.abspath(".."))

extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinxcontrib.httpdomain",
    "sphinx_gallery.gen_gallery",
]

suppress_warnings = ["image.nonlocal_uri"]
templates_path = ["_templates"]
source_suffix = ".rst"
master_doc = "index"

project = "PyTorch Sphinx Theme"
copyright = "PyTorch"
version = "0.1"
release = "0.1"
language = "en"

exclude_patterns = []
pygments_style = "default"
intersphinx_mapping = {"rtd": ("https://docs.readthedocs.io/en/latest/", None)}

html_theme = "sphinx_rtd_theme"
html_show_sourcelink = False
htmlhelp_basename = "DFFSphinxThemeDemoDoc"

examples = glob.glob("../examples")

sphinx_gallery_conf = {
    "examples_dirs": examples,  # path to your example scripts
    "gallery_dirs": "examples",  # path to where to save gallery generated output
    "filename_pattern": ".py",
    "reset_argv": lambda _, __: ["-a"],
    "within_subsection_order": FileNameSortKey,
    "ignore_pattern": f"{re.escape(os.sep)}_",
}

if not os.path.exists("examples"):
    os.makedirs("examples")
for support_file in [example for example in examples if os.path.basename(example).startswith("_")]:
    shutil.copyfile(support_file, f"examples/{os.path.basename(support_file)}")

latex_documents = [
    ("index", "PyTorchthemedemo.tex", "PyTorch theme demo Documentation", "PyTorch, PyTorch", "manual"),
]
man_pages = [("index", "pytorchthemedemo", "PyTorch theme demo Documentation", ["PyTorch"], 1)]
texinfo_documents = [
    (
        "index",
        "PyTorchthemedemo",
        "PyTorch theme demo Documentation",
        "PyTorch",
        "PyTorchthemedemo",
        "One line description of project.",
        "Miscellaneous",
    ),
]
