import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()
setuptools.setup(
    name="dff",
    version="1.95",
    scripts=[],
    author="James Finch",
    author_email="jdfinch@emory.edu",
    description="Library for creating state-machine-based chatbots.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=setuptools.find_packages(),
    install_requires=[
        "structpy==0.3",
        "lark-parser",
        "regex",
        #  "nltk",
        "importlib_resources",
        "pytz",
        #  "spacy",
        "dill",
        "pathos",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_data={"dff": ["state_transition_dialogue_manager/data/*.json"]},
    include_package_data=True,
)
