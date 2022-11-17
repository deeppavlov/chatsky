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
    "nest_asyncio>=1.5.5",
    "typing_extensions>=4.0.0",
]

doc = [
    "sphinx>=1.7.9",
    "dff_sphinx_theme>=0.1.5",
    "sphinxcontrib-apidoc==0.3.0",
    "sphinxcontrib-httpdomain>=1.8.0",
    "sphinxcontrib-katex==0.9.0",
    "sphinx_copybutton>=0.5",
    "sphinx_gallery>=0.11.1",
    "sphinx-autodoc-typehints>=1.19.4",
    "nbsphinx>=0.8.9",
    "jupytext>=1.14.1",
    "jupyter>=1.0.0",
]

mypy_dependencies = [
    "mypy==0.991",
]

sqlite_dependencies = [
    "sqlalchemy>=1.4.27",
]

redis_dependencies = [
    "redis>=4.1.2",
]

mongodb_dependencies = [
    "pymongo>=4.0.2",
    "bson>=0.5.10",
]

mysql_dependencies = [
    "sqlalchemy>=1.4.27",
    "pymysql>=1.0.2",
    "cryptography>=36.0.2",
]

postgresql_dependencies = [
    "sqlalchemy>=1.4.27",
    "psycopg2-binary==2.9.4",  # TODO: change to >= when psycopg2 will be stabe for windows
]

ydb_dependencies = [
    "ydb>=2.5.0",
]

test_requirements = [
    "pytest >=6.2.4,<7.0.0",
    "pytest-cov >=2.12.0,<3.0.0",
    "pytest-asyncio >=0.14.0,<0.15.0",
    "flake8 >=3.8.3,<4.0.0",
    "click<=8.0.4",
    "black ==20.8b1",
    "isort >=5.0.6,<6.0.0",
    "flask[async]>=2.1.2",
    "psutil>=5.9.1",
    "requests>=2.28.1",
]

devel = [
    "bump2version>=1.0.1",
    "build==0.7.0",
    "twine==4.0.0",
]

full = merge_req_lists(
    [
        core,
        sqlite_dependencies,
        redis_dependencies,
        mongodb_dependencies,
        mysql_dependencies,
        postgresql_dependencies,
        ydb_dependencies,
    ]
)

tests_full = merge_req_lists(
    [
        full,
        test_requirements,
    ]
)

devel_full = merge_req_lists(
    [
        tests_full,
        doc,
        devel,
        mypy_dependencies,
    ]
)

EXTRA_DEPENDENCIES = {
    "doc": doc,
    "tests": test_requirements,
    "devel": devel,
    "full": full,
    "test_full": tests_full,
    "devel_full": devel_full,
    "sqlite": sqlite_dependencies,
    "redis": redis_dependencies,
    "mongodb": mongodb_dependencies,
    "mysql": mysql_dependencies,
    "postgresql": postgresql_dependencies,
    "ydb": ydb_dependencies,
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
    include_package_data=True,
    python_requires=">=3.7, <4",
    install_requires=core,  # Optional
    test_suite="tests",
    extras_require=EXTRA_DEPENDENCIES,
)
