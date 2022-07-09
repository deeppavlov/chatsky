
# Dialog Flow Script Parser

**Dialog Flow Script Parser** is python module add-on for [Dialog Flow Framework](https://github.com/deepmipt/dialog_flow_framework), a free and open-source software stack for creating chatbots, released under the terms of Apache License 2.0.


[Dialog Flow Script Parser](../..) allows you to parse python files in order to extract inputs and dictionaries.
[![Codestyle](https://github.com/deepmipt/dialog_flow_parser/actions/workflows/codestyle.yml/badge.svg)](https://github.com/deepmipt/dialog_flow_parser/actions)
[![Tests](https://github.com/deepmipt/dialog_flow_parser/actions/workflows/test_coverage.yml/badge.svg)](https://github.com/deepmipt/dialog_flow_parser/actions)
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
usage: df_script_parser.py2yaml [-h] INPUT_FILE OUTPUT_DIR

Parse python script INPUT_FILE into import.yaml containing information about imports used in the script,
script.yaml containing a dictionary found inside the file.
If the file contains an instance of df_engine.Actor class its arguments will be parsed and special labels will be placed in script.yaml.

All the files are stored in OUTPUT_DIR.

positional arguments:
  INPUT_FILE  Python script to parse.
  OUTPUT_DIR  Directory to store parser output in.

optional arguments:
  -h, --help  show this help message and exit
```

**_NOTE:_** Use `py2yaml` parser in the same python environment that is used to launch the script otherwise site packages will not be found.


### File formats

File `INPUT_FILE` should be a `.py` file with the following structure:
1. It may have any import statements except for star imports (`from . import *`).
2. It may have one `dict` declaration.
3. It may have one `df_engine.core.Actor` call.

The `OUTPUT_DIR` will contain:
1. File `import.yaml` containing information about modules imported in the script. The file has 3 keys: (`pypi`, `system`, `local`). Each value is a dictionary with additional package information as key and code that imports that module as value.
   1. Modules installed via pip are placed under the `pypi` key. The additional information for such modules is a string that goes after `pip install` in order to install the package.
   2. System modules are placed under the `system` key. The additional information for such modules is the module's name.
   3. Local modules are placed under the `local` key. The additional information for such modules is the path to the file. The path is relative if possible.
2. File `script.yaml` containing the dictionary's structure. Any objects in the dictionary except for other dictionaries and lists are replaced with their string representation. If given imports it is unclear whether a string is a python code or just a string tag `!str` is applied.
   * If the `INPUT_FILE` has a `df_engine.core.Actor` call its arguments `start_label` and `fallback_label` are marked in the `script.yaml` with the `!start`, `!start:str`, `!fallback` or `!fallback:str` tags.


## yaml2py

```bash
df_script_parser.yaml2py --help
```

```
usage: df_script_parser.yaml2py [-h] INPUT_DIR OUTPUT_FILE

Generate a python script OUTPUT_FILE from import.yaml and script.yaml inside the INPUT_DIR.

Generation rules:

* If a string inside the script.yaml is a correct python code within the context of imports it will be displayed in the OUTPUT_FILE without quotations.
If you want to specify how the string should be displayed use !str tag for strings and !py tag for lines of code.

* If a {dictionary {key / value} / list value} has a !start or !start:str or !start:py tag the path to that element will be stored in a start_label variable.

* If a {dictionary {key / value} / list value} has a tag !fallback or !fallback:str or !fallback:py tag the path to that key will be stored in a fallback_label variable.

positional arguments:
  INPUT_DIR    Directory with yaml files.
  OUTPUT_FILE  Python file, output.

optional arguments:
  -h, --help   show this help message and exit
```


### File formats

File `OUTPUT_FILE` contains a python script with a `df_engine.core.Actor` call the arguments of which are extracted from the `INPUT_DIR/script.yaml` file.

All the imports from `INPUT_DIR/import.yaml` are imported in the `OUTPUT_FILE`.

If a script has a string instance inside of it, it is displayed in the `OUTPUT_FILE` without quotations if the string is a valid python expression in the context of imports. If it is not a valid python expression it is displayed with quotations. If a string should be displayed with quotations even though it is a valid python expression use the `!str` tag. If a string should be displayed without the quotations use the `!py` tag.

If a script has a tag `!start` or `!start:str` or `!start:py` the path to that tag is stored inside the `start_label` variable. Tag `!start` is used to let the program decide whether to use quotations. This behavior may be specified using the `!start:str` and `!start:py` tags.

If a script has a tag `!fallback` or `!fallback:str` or `!fallback:py` the path to that tag is stored inside the `fallback_label` variable. Tag `!fallback` is used to let the program decide whether to use quotations. This behavior may be specified using the `!fallback:str` and `!fallback:py` tags.


To get more advanced examples, take a look at [examples](examples) on GitHub.


# Contributing to the Dialog Flow Script Parser

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md).