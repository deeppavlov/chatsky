
# Dialog Flow Script Parser

**Dialog Flow Script Parser** is python module add-on for [Dialog Flow Framework](https://github.com/deeppavlovteam/dialog_flow_framework), a free and open-source software stack for creating chatbots, released under the terms of Apache License 2.0.


[Dialog Flow Script Parser](../..) allows you to parse python files in order to extract inputs and dictionaries.
[![Codestyle](https://github.com/deeppavlovteam/dialog_flow_parser/actions/workflows/codestyle.yml/badge.svg)](https://github.com/deeppavlovteam/dialog_flow_parser/actions)
[![Tests](https://github.com/deeppavlovteam/dialog_flow_parser/actions/workflows/test_coverage.yml/badge.svg)](https://github.com/deeppavlovteam/dialog_flow_parser/actions)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
![Python 3.6, 3.7, 3.8, 3.9](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-green.svg)

<!-- TODO: uncomment one of these to add badges to your project description -->
<!-- [![Documentation Status](https://df_script_parser.readthedocs.io/en/stable/?badge=stable)]() See readthedocs.io -->
<!-- [![Coverage Status]()]() See coveralls.io -->
<!-- [![PyPI](https://img.shields.io/pypi/v/df_script_parser)](https://pypi.org/project/df_script_parser/) -->
<!-- [![Downloads](https://pepy.tech/badge/df_script_parser)](https://pepy.tech/project/df_script_parser) -->

# Quick Start
## Installation
```bash
pip install df_script_parser
```

## py2yaml

```bash
df_script_parser.py2yaml --help
```

```
usage: df_script_parser.py2yaml [-h] [--requirements REQUIREMENTS] ROOT_FILE PROJECT_ROOT_DIR OUTPUT_FILE

Compress a dff project into a yaml file by parsing files inside PROJECT_ROOT_DIR starting with ROOT_FILE.
Extract imports, assignments of dictionaries and function calls from each file.
Recursively parse imported local modules.
Collect non-local modules as project requirements

positional arguments:
  ROOT_FILE             Python file to start parsing with
  PROJECT_ROOT_DIR      Directory that contains all the local files required to run ROOT_FILE
  OUTPUT_FILE           Yaml file to store parser output in

optional arguments:
  -h, --help            show this help message and exit
  --requirements REQUIREMENTS
                        File with project requirements to override those collected by parser
```

**_NOTE:_** Use `py2yaml` parser in the same python environment that is used to launch the script otherwise site packages will not be found.
**_NOTE:_** Any assignments of function calls in which the function being called is ``df_engine.core.Actor`` will be checked for correctness of the arguments passed to the function.

### File formats

The `OUTPUT_FILE` will contain:
1. ``requirements`` key which points to a list of project requirements collected by parser.
   If optional argument ``REQUIREMENTS`` was specified replace the list with a list of requirements from that file
2. ``namespaces`` key which points to a dictionary with all the parsed files. Keys are the names of those
   modules that could be used to import it from ``PROJECT_ROOT_DIR`` or its parent directory if ``PROJECT_ROOT_DIR``
   contains a ``__init__.py`` file. The values are dictionaries in which keys are the names of the objects inside the module
   while values are their definitions.


## yaml2py

```bash
df_script_parser.yaml2py --help
```

```
usage: df_script_parser.yaml2py [-h] YAML_FILE EXTRACT_TO_DIRECTORY

Extract project from a yaml file to a directory

positional arguments:
  YAML_FILE             Yaml file to load
  EXTRACT_TO_DIRECTORY  Path to the directory to extract project to

optional arguments:
  -h, --help            show this help message and exit
```

## Examples

To get more advanced examples, take a look at [examples](examples/examples.ipynb).


# Contributing to the Dialog Flow Script Parser

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md).