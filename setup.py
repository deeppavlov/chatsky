#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pip
import pathlib

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
from setuptools import find_packages


LOCATION = pathlib.Path(__file__).parent.resolve()


def parse_requirements(filename):
    """load requirements from a pip requirements file"""
    lines = (line.strip() for line in (LOCATION / filename).open())
    return [line for line in lines if line and not line.startswith("#")]


# Get the long description from the README file
readme_file = LOCATION / "README.md"

readme_lines = [line.strip() for line in readme_file.open(encoding="utf-8").readlines()]
description = [line for line in readme_lines if line and not line.startswith("#")][0]
long_description = "\n".join(readme_lines)


requirements = parse_requirements("requirements.txt")

test_requirements = parse_requirements("requirements_test.txt")


setup(
    name="df_extended_conditions",
    version="0.1.0",
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ruthenian8/dialog_flow_transitions",
    author="Denis Kuznetsov",
    author_email="kuznetosv.den.p@gmail.com",
    classifiers=[  # Optional
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 2 - Pre-Alpha",
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
    keywords=["chatbots", "Dialog Flow Transitions"],  # Optional
    packages=find_packages(where="."),  # Required
    include_package_data=True,
    python_requires=">=3.6, <4",
    install_requires=requirements,
    test_suite="tests",
    tests_require=test_requirements,
    extras_require={
        "async": ["httpx>=0.23.0"],
        "hf": ["transformers>=4.16.2", "torch>=1.7.0", "scikit-learn<=1.1.1"],
        "gensim": ["gensim>=4.0.0", "scikit-learn<=1.1.1"],
        "sklearn": ["scikit-learn<=1.1.1"],
        "dialogflow": ["google-cloud-dialogflow==2.15.0"],
        "all": [
            "transformers>=4.16.2",
            "torch>=1.7.0",
            "scikit-learn<=1.1.1",
            "gensim>=4.0.0",
            "scikit-learn<=1.1.1", 
            "google-cloud-dialogflow==2.15.0"
        ]
    }
)
