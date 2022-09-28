"""This module contains cli wrappers around parser tools
"""
from pathlib import Path
import argparse
from df_script_parser.tools import py2yaml, yaml2py, py2graph


def is_dir(arg: str) -> Path:
    """Check that the passed argument is a directory

    :param arg: Argument to check
    :type arg: str
    :return: :py:class:`.Path` instance created from arg if it is a directory
    """
    path = Path(arg)
    if path.is_dir():
        return path
    raise argparse.ArgumentTypeError(f"Not a directory: {path}")


def is_file(arg: str) -> Path:
    """Check that the passed argument is a file

    :param arg: Argument to check
    :type arg: str
    :return: :py:class:`.Path` instance created from arg if it is a file
    """
    path = Path(arg)
    if path.is_file():
        return path
    raise argparse.ArgumentTypeError(f"Not a file: {path}")


def py2yaml_cli():
    """:py:func:`.py2yaml` cli wrapper"""
    parser = argparse.ArgumentParser(description=py2yaml.__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument(
        "root_file",
        metavar="ROOT_FILE",
        help="Python file to start parsing with",
        type=is_file,
    )
    parser.add_argument(
        "project_root_dir",
        metavar="PROJECT_ROOT_DIR",
        help="Directory that contains all the local files required to run ROOT_FILE",
        type=is_dir,
    )
    parser.add_argument(
        "output_file",
        metavar="OUTPUT_FILE",
        help="Yaml file to store parser output in",
        type=str,
    )
    parser.add_argument(
        "--requirements",
        metavar="REQUIREMENTS",
        help="File with project requirements to override those collected by parser",
        type=is_file,
        required=False,
        default=None,
    )
    args = parser.parse_args()
    py2yaml(**vars(args))


def py2graph_cli():
    """:py:func:`.py2graph` cli wrapper"""
    parser = argparse.ArgumentParser(description=py2graph.__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument(
        "root_file",
        metavar="ROOT_FILE",
        help="Python file to start parsing with",
        type=is_file,
    )
    parser.add_argument(
        "project_root_dir",
        metavar="PROJECT_ROOT_DIR",
        help="Directory that contains all the local files required to run ROOT_FILE",
        type=is_dir,
    )
    parser.add_argument(
        "output_file",
        metavar="OUTPUT_FILE",
        help="Yaml file to store parser output in",
        type=str,
    )
    parser.add_argument(
        "--requirements",
        metavar="REQUIREMENTS",
        help="File with project requirements to override those collected by parser",
        type=is_file,
        required=False,
        default=None,
    )
    args = parser.parse_args()
    py2graph(**vars(args))


def yaml2py_cli():
    """:py:func:`.yaml2py` cli wrapper"""
    parser = argparse.ArgumentParser(description=yaml2py.__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument(
        "yaml_file",
        metavar="YAML_FILE",
        help="Yaml file to load",
        type=is_file,
    )
    parser.add_argument(
        "extract_to_directory",
        metavar="EXTRACT_TO_DIRECTORY",
        help="Path to the directory to extract project to",
        type=is_dir,
    )
    args = parser.parse_args()
    yaml2py(**vars(args))
