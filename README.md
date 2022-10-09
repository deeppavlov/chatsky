
# df_script_viewer

**df_script_viewer** is python module add-on for [Dialog Flow Framework](https://github.com/deepmipt/dialog_flow_framework), a free and open-source software stack for creating chatbots, released under the terms of Apache License 2.0.

Using DF Script Viewer, you can get a visual representation of the plot that you are working on at any time. This feature gives you more control over the development process.


[df_script_viewer](../..) allows you to ...
[![Codestyle](../../../workflows/codestyle/badge.svg)](../../../actions)
[![Tests](../../../workflows/test_coverage/badge.svg)](../../../actions)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
![Python 3.6, 3.7, 3.8, 3.9](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-green.svg)

<!-- TODO: uncomment one of these to add badges to your project description -->
<!-- [![Documentation Status](https://df_script_viewer.readthedocs.io/en/stable/?badge=stable)]() See readthedocs.io -->
<!-- [![Coverage Status]()]() See coveralls.io -->
<!-- [![PyPI](https://img.shields.io/pypi/v/df_script_viewer)](https://pypi.org/project/df_script_viewer/) -->
<!-- [![Downloads](https://pepy.tech/badge/df_script_viewer)](https://pepy.tech/project/df_script_viewer) -->

# Quick Start
## Installation
```bash
pip install df_script_viewer
```

## Basic example

Get a DFF project project plot as a static image:

```bash
df_script_viewer.image ./examples/python_files/main.py ./examples/python_files/ ./plot.png
```

View the project plot on a local Dash server:

```bash
df_script_viewer.server ./examples/python_files/main.py ./examples/python_files/
```

# Contributing to the df_script_viewer

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md).