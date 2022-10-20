#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pathlib
from typing import Iterable, List

from setuptools import setup, find_packages


LOCATION = pathlib.Path(__file__).parent.resolve()


# Get the long description from the README file
readme_file = LOCATION / "README.md"

readme_lines = [line.strip() for line in readme_file.open(encoding="utf-8").readlines()]
description = [line for line in readme_lines if line and not line.startswith("#")][0]
long_description = "\n".join(readme_lines)


def merge_req_lists(req_lists: Iterable[List[str]]) -> List[str]:
    result: set[str] = set()
    for req_list in req_lists:
        for req in req_list:
            result.add(req)
    return list(result)


core = [
    "pydantic>=1.8.2",
]

doc = [
    "sphinx>=1.7.9",
    "dff_sphinx_theme>=0.1.3",
    "sphinxcontrib-apidoc==0.3.0",
    "sphinxcontrib-httpdomain>=1.8.0",
    "sphinxcontrib-katex==0.9.0",
    "sphinx_copybutton>=0.5",
    "sphinx_gallery>=0.11.1",
    "matplotlib>=3.6.0",
]

mypy_dependencies = [
    "mypy",
]

devel = [
    "bump2version>=1.0.1",
    "build==0.7.0",
    "twine==4.0.0",
    "pytest >=6.2.4,<7.0.0",
    "pytest-cov >=2.12.0,<3.0.0",
    "pytest-asyncio >=0.14.0,<0.15.0",
    "flake8 >=3.8.3,<4.0.0",
    "click<=8.0.4",
    "black ==20.8b1",
    "isort >=5.0.6,<6.0.0",
]

full = merge_req_lists([
    core
])

devel_full = merge_req_lists([
    full,
    doc,
    devel,
    mypy_dependencies,
])

EXTRA_DEPENDENCIES = {
    "doc": doc,
    "devel": devel,
    "full": full,
    "devel_full": devel_full,
}

setup(
    name="dff",
    version="0.10.1",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/deeppavlov/dialog_flow_framework",
    author="Denis Kuznetsov",
    author_email="kuznetsov.den.p@gmail.com",
    classifiers=[  # Optional
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords="chatbots",  # Optional
    packages=find_packages(where="."),  # Required
    python_requires=">=3.7, <4",
    install_requires=core,  # Optional
    test_suite="tests",
    extras_require=EXTRA_DEPENDENCIES,
)
