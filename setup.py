from setuptools import setup, find_packages
import pathlib
import sys
import re

native_type_patterns = {re.compile(r"\b(" + t + r")\["): t.capitalize() + "[" for t in ["dict", "list", "tuple"]}
cache_patterns = {re.compile(r"\bfunctools.cache\b"): "functools.lru_cache(maxsize=None)"}
fstring_patterns = {re.compile(r"\=\}"): "}"}
forwardref_patterns = {
    re.compile("from typing import ForwardRef"): "",
    re.compile(r'ForwardRef\("Context"\)'): "BaseModel",
}


def downgrade(root_dir: pathlib.Path):
    py_files = sum(
        [list(root_dir.glob(glob)) for glob in ["tests/*.py", "examples/*.py", "dff/*.py", "dff/core/*.py"]], []
    )
    for py_file in py_files:
        text = py_file.read_text()
        if sys.version_info < (3, 9):
            if any([i.search(text) for i in native_type_patterns.keys()]):
                text = "from typing import Dict, List, Tuple\n{}".format(text)
                for pat, replace in native_type_patterns.items():
                    text = pat.sub(replace, text)
            for pat, replace in cache_patterns.items():
                text = pat.sub(replace, text)
        if sys.version_info < (3, 8):
            for pat, replace in fstring_patterns.items():
                text = pat.sub(replace, text)
        if sys.version_info < (3, 7):
            for pat, replace in forwardref_patterns.items():
                text = pat.sub(replace, text)
        py_file.write_text(text)


LOCATION = pathlib.Path(__file__).parent.resolve()

downgrade(LOCATION)
# Get the long description from the README file
readme_file = LOCATION / "README.md"

readme_lines = [line.strip() for line in readme_file.open(encoding="utf-8").readlines()]
description = [line for line in readme_lines if line and not line.startswith("#")][0]
long_description = "\n".join(readme_lines)


def read_requirements():
    """parses requirements from requirements.txt"""
    reqs_file = LOCATION / "requirements.txt"
    reqs = [line.strip() for line in reqs_file.open(encoding="utf8").readlines() if not line.strip().startswith("#")]

    names = []
    links = []
    for req in reqs:
        if "://" in req:
            links.append(req)
        else:
            names.append(req)
    return {"install_requires": names, "dependency_links": links}


setup(
    name="dff",
    version="0.1.a1",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/deepmipt/dialog_flow_framework",
    author="Denis Kuznetsov",
    author_email="kuznetsov.den.p@gmail.com",
    classifiers=[  # Optional
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords="chatbots",  # Optional
    # package_dir={"": "dff"},  # Optional
    packages=find_packages(where="."),  # Required
    python_requires=">=3.6, <4",
    install_requires=["pydantic==1.8.2"],  # Optional
    # extras_require={"dev": ["check-manifest"], "test": ["coverage"]}, # Optional
    # package_data={"sample": ["package_data.dat"]}, # Optional
    # data_files=[("my_data", ["data/data_file"])],  # Optional
    #
    # For example, the following would provide a command called `sample` which
    # executes the function `main` from this package when invoked:
    # entry_points={"console_scripts": ["sample=sample:main"]},  # Optional
    # project_urls={},  # Optional
)
