
Installation
============


``pip install dff[parser]``

or


``pip install dff[parser, graph]``

for graph export functionality.

py2yaml
=======


``dff.py2yaml --help``


::

    usage: dff.py2yaml [-h] ROOT_FILE PROJECT_ROOT_DIR OUTPUT_FILE

    Compress a dff project into a yaml file by parsing files inside PROJECT_ROOT_DIR starting with ROOT_FILE.
    Extract imports, assignments of dictionaries and function calls from each file.
    Recursively parse imported local modules.

    positional arguments:
      ROOT_FILE             Python file to start parsing with
      PROJECT_ROOT_DIR      Directory that contains all the local files required to run ROOT_FILE
      OUTPUT_FILE           Yaml file to store parser output in

    optional arguments:
      -h, --help            show this help message and exit


**NOTE:** Use ``py2yaml`` parser in the same python environment that is used to launch the script otherwise site packages will not be found.

**NOTE:** Any assignments of function calls in which the function being called is ``df_engine.core.Actor`` will be checked for correctness of the arguments passed to the function.

File formats
------------

The ``OUTPUT_FILE`` will contain:

1. ``namespaces`` key which points to a dictionary with all the parsed files. Keys are the names of those
   modules that could be used to import it from ``PROJECT_ROOT_DIR`` or its parent directory if ``PROJECT_ROOT_DIR``
   contains a ``__init__.py`` file. The values are dictionaries in which keys are the names of the objects inside the module
   while values are their definitions.


yaml2py
=======


``dff.yaml2py --help``


::

    usage: dff.yaml2py [-h] YAML_FILE EXTRACT_TO_DIRECTORY

    Extract project from a yaml file to a directory

    positional arguments:
      YAML_FILE             Yaml file to load
      EXTRACT_TO_DIRECTORY  Path to the directory to extract project to

    optional arguments:
      -h, --help            show this help message and exit
