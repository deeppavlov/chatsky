import pathlib
import setuptools


LOCATION = pathlib.Path(__file__).parent.resolve()


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


readme_file = LOCATION / "README.md"
long_description = readme_file.open(encoding="utf8").read()

setuptools.setup(
    name="dff",
    version="0.1.0",
    scripts=[],
    author="Denis Kuznetsov",
    author_email="kuznetsov.den.p@gmail.com",
    description="Library for creating state-machine-based chatbots.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/deepmipt/dialog_flow_framework",
    packages=setuptools.find_packages(exclude=("docs", "examples", "tests")),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    package_data={},
    include_package_data=True,
    python_requires=">=3.9",
    **read_requirements()
)
