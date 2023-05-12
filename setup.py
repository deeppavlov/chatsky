#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pathlib
from typing import List

from setuptools import setup, find_packages


LOCATION = pathlib.Path(__file__).parent.resolve()


# Get the long description from the README file
readme_file = LOCATION / "README.md"

readme_lines = [line.strip() for line in readme_file.open(encoding="utf-8").readlines()]
description = [line for line in readme_lines if line and not line.startswith("#")][0]
long_description = "\n".join(readme_lines)


def merge_req_lists(*req_lists: List[str]) -> List[str]:
    result: set[str] = set()
    for req_list in req_lists:
        for req in req_list:
            result.add(req)
    return list(result)


core = [
    "pydantic~=1.10.7",
    "nest-asyncio~=1.5.6",
    "typing-extensions~=4.5.0",
]

async_files_dependencies = [
    "aiofiles~=23.1.0",
]

redis_dependencies = [
    "redis~=4.5.4",
]

mongodb_dependencies = [
    "motor~=3.1.2",
]

_sql_dependencies = [
    "sqlalchemy[asyncio]~=2.0.10",
]

sqlite_dependencies = merge_req_lists(
    _sql_dependencies,
    [
        "aiosqlite~=0.19.0",
    ],
)

mysql_dependencies = merge_req_lists(
    _sql_dependencies,
    [
        "asyncmy~=0.2.7",
        "cryptography~=40.0.2",
    ],
)

postgresql_dependencies = merge_req_lists(
    _sql_dependencies,
    [
        "asyncpg~=0.27.0",
    ],
)

ydb_dependencies = [
    "ydb~=2.5.0",
    "six~=1.16.0",
]

telegram_dependencies = [
    "pytelegrambotapi~=4.5.1",
]

full = merge_req_lists(
    core,
    async_files_dependencies,
    sqlite_dependencies,
    redis_dependencies,
    mongodb_dependencies,
    mysql_dependencies,
    postgresql_dependencies,
    ydb_dependencies,
    telegram_dependencies,
)

requests_requirements = [
    "requests~=2.28.2",
]

test_requirements = merge_req_lists(
    [
        "pytest~=7.3.1",
        "pytest-cov~=4.0.0",
        "pytest-asyncio~=0.14.0",
        "flake8~=3.9.2",
        "click~=8.0.4",
        "black~=20.8b1",
        "isort~=5.11.5",
        "flask[async]~=2.2.3",
        "psutil~=5.9.5",
        "telethon~=1.28.5",
        "anyio~=3.6.2",
        "fastapi~=0.95.1",
        "idna~=3.4.0",
        "sniffio~=1.3.0",
        "starlette~=0.26.1",
        "h11~=0.14.0",
        "uvicorn~=0.21.1",
        "websockets~=11.0.2",
        "locust~=2.15",
    ],
    requests_requirements,
)

tests_full = merge_req_lists(
    full,
    test_requirements,
)

doc = merge_req_lists(
    [
        "sphinx~=5.3.0",
        "pydata-sphinx-theme~=0.13.3",
        "sphinxcontrib-apidoc~=0.3.0",
        "sphinxcontrib-httpdomain~=1.8.0",
        "sphinxcontrib-katex~=0.9.0",
        "sphinx-favicon~=1.0.1",
        "sphinx-copybutton~=0.5.2",
        "sphinx-gallery~=0.7.0",
        "sphinx-autodoc-typehints~=1.23.0",
        "nbsphinx~=0.9.1",
        "jupytext~=1.14.5",
        "jupyter~=1.0.0",
    ],
    requests_requirements,
)

devel = [
    "bump2version~=1.0.1",
    "build~=0.7.0",
    "twine~=4.0.0",
]

mypy_dependencies = [
    "mypy~=0.950",
]

devel_full = merge_req_lists(
    tests_full,
    doc,
    devel,
    mypy_dependencies,
)

EXTRA_DEPENDENCIES = {
    "core": core,  # minimal dependencies (by default)
    "json": async_files_dependencies,  # dependencies for using JSON
    "pickle": async_files_dependencies,  # dependencies for using Pickle
    "sqlite": sqlite_dependencies,  # dependencies for using SQLite
    "redis": redis_dependencies,  # dependencies for using Redis
    "mongodb": mongodb_dependencies,  # dependencies for using MongoDB
    "mysql": mysql_dependencies,  # dependencies for using MySQL
    "postgresql": postgresql_dependencies,  # dependencies for using PostgreSQL
    "ydb": ydb_dependencies,  # dependencies for using Yandex Database
    "telegram": telegram_dependencies,  # dependencies for using Telegram
    "full": full,  # full dependencies including all options above
    "tests": test_requirements,  # dependencies for running tests
    "test_full": tests_full,  # full dependencies for running all tests (all options above)
    "tutorials": tests_full,  # dependencies for running tutorials (all options above)
    "devel": devel,  # dependencies for development
    "doc": doc,  # dependencies for documentation
    "devel_full": devel_full,  # full dependencies for development (all options above)
}

setup(
    name="dff",
    version="0.4.1",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/deeppavlov/dialog_flow_framework",
    author="Denis Kuznetsov",
    author_email="kuznetsov.den.p@gmail.com",
    classifiers=[
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
    keywords="chatbots",
    packages=find_packages(where="."),
    include_package_data=True,
    python_requires=">=3.7, <4",
    install_requires=core,
    test_suite="tests",
    extras_require=EXTRA_DEPENDENCIES,
)
