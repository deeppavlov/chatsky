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

async_files_dependencies = [
    "aiofiles>=22.1.0",
]

redis_dependencies = [
    "aioredis>=2.0.1",
]

mongodb_dependencies = [
    "motor>=3.1.1",
]

_sql_dependencies = [
    "sqlalchemy[asyncio]>=2.0.2",
]

sqlite_dependencies = merge_req_lists(
    [
        _sql_dependencies,
        [
            "aiosqlite>=0.18.0",
            "sqlalchemy[asyncio]>=1.4.27",
        ],
    ]
)

mysql_dependencies = merge_req_lists(
    [
        _sql_dependencies,
        [
            "asyncmy>=0.2.5",
            "cryptography>=36.0.2",
        ],
    ]
)

postgresql_dependencies = merge_req_lists(
    [
        _sql_dependencies,
        [
            "asyncpg>=0.27.0",
        ],
    ]
)

ydb_dependencies = [
    "ydb>=2.5.0",
    "six>=1.16.0",
]

telegram_dependencies = [
    "pytelegrambotapi==4.5.1",
]

parser_dependencies = [
    "cached-property==1.5.2; python_version<'3.8'",
    "astunparse==1.6.3; python_version<'3.9'",
    "ruamel.yaml",
    "networkx",
]

script_viewer_dependencies = merge_req_lists(
    [
        parser_dependencies,
        [
            "graphviz==0.17",
            "dash==2.6.2",
            "hupper==1.11",
            "watchdog==3.0.0",
            "plotly<=5.10.0",
        ],
    ]
)

full = merge_req_lists(
    [
        core,
        async_files_dependencies,
        sqlite_dependencies,
        redis_dependencies,
        mongodb_dependencies,
        mysql_dependencies,
        postgresql_dependencies,
        ydb_dependencies,
        telegram_dependencies,
        parser_dependencies,
        script_viewer_dependencies,
    ]
)

test_requirements = [
    "pytest >=7.2.1,<8.0.0",
    "pytest-cov >=4.0.0,<5.0.0",
    "pytest-asyncio >=0.14.0,<0.15.0",
    "flake8==6.0.0; python_version>'3.7'",
    "flake8<=5.0.4; python_version=='3.7'",
    "pyflakes==3.0.1; python_version>'3.7'",
    "pyflakes<=2.5.0; python_version=='3.7'",
    "click<=8.0.4",
    "black ==20.8b1",
    "isort >=5.0.6,<6.0.0",
    "flask[async]>=2.1.2",
    "psutil>=5.9.1",
    "requests>=2.28.1",
    "telethon>=1.27.0,<2.0",
]

tests_full = merge_req_lists(
    [
        full,
        test_requirements,
    ]
)

doc = [
    "sphinx<6",
    "pydata_sphinx_theme>=0.12.0",
    "sphinxcontrib-apidoc==0.3.0",
    "sphinxcontrib-httpdomain>=1.8.0",
    "sphinxcontrib-katex==0.9.0",
    "sphinx_copybutton>=0.5",
    "sphinx_gallery==0.7.0",
    "sphinx-autodoc-typehints>=1.19.4",
    "nbsphinx>=0.8.9",
    "jupytext>=1.14.1",
    "jupyter>=1.0.0",
]

devel = [
    "bump2version>=1.0.1",
    "build==0.7.0",
    "twine==4.0.0",
]

mypy_dependencies = [
    "mypy==1.1.1",
    "networkx-stubs==0.0.1",
]

devel_full = merge_req_lists(
    [
        tests_full,
        doc,
        devel,
        mypy_dependencies,
    ]
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
    "parser": parser_dependencies,  # dependencies for using parser
    "viewer": script_viewer_dependencies,  # dependencies for script viewer
    "full": full,  # full dependencies including all options above
    "tests": test_requirements,  # dependencies for running tests
    "test_full": tests_full,  # full dependencies for running all tests (all options above)
    "examples": tests_full,  # dependencies for running examples (all options above)
    "devel": devel,  # dependencies for development
    "doc": doc,  # dependencies for documentation
    "devel_full": devel_full,  # full dependencies for development (all options above)
}

setup(
    name="dff",
    version="0.3.2",
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
    entry_points={
        "console_scripts": [
            "dff.viewer.server=dff.utils.viewer:make_server",
            "dff.viewer.image=dff.utils.viewer:make_image",
        ]
    },
)
