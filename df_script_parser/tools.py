"""This module contains implementations of :py:func:`.py2yaml` and :py:func:`.yaml2py` parsers
"""
from pathlib import Path
import typing as tp
import logging
import json

from black import format_file_in_place, FileMode, WriteBack
import networkx as nx  # type: ignore

from df_script_parser.dumpers_loaders import yaml_dumper_loader
from df_script_parser.processors.dict_processors import DictProcessor
from df_script_parser.processors.recursive_parser import RecursiveParser
from df_script_parser.utils.namespaces import Import, From, Call
from df_script_parser.utils.exceptions import DictStructureError


def py2yaml(
    root_file: Path,
    project_root_dir: Path,
    output_file: Path,
    requirements: tp.Optional[Path] = None,
):
    """Compress a dff project into a yaml file by parsing files inside PROJECT_ROOT_DIR starting with ROOT_FILE.
    Extract imports, assignments of dictionaries and function calls from each file.
    Recursively parse imported local modules. Collect non-local modules as project requirements

    :param root_file: Python file to start parsing with
    :type root_file: :py:class:`.Path`
    :param project_root_dir: Directory that contains all the local files required to run ``root_file``
    :type project_root_dir: :py:class:`.Path`
    :param output_file: Yaml file to store parser output in
    :type output_file: :py:class:`.Path`
    :param requirements: Path to a file containing project requirements, defaults to None
    :type requirements: :pu:class:`.Path`, optional
    :return:
    """
    with open(Path(output_file).absolute(), "w", encoding="utf-8") as outfile:
        dictionary = RecursiveParser(Path(project_root_dir).absolute()).parse_project_dir(Path(root_file).absolute())

        if requirements:
            with open(requirements, "r", encoding="utf-8") as reqs:
                dictionary["requirements"] = [x for x in reqs.read().split("\n") if x]

        yaml_dumper_loader.dump(dictionary, outfile)


def py2graph(
    root_file: Path,
    project_root_dir: Path,
    output_file: Path,
    requirements: tp.Optional[Path] = None,
):
    """Export dff project dir as a :py:mod:`networkx` graph.

    :param root_file: Python file to start parsing with
    :type root_file: :py:class:`.Path`
    :param project_root_dir: Directory that contains all the local files required to run ``root_file``
    :type project_root_dir: :py:class:`.Path`
    :param output_file: Yaml file to store parser output in
    :type output_file: :py:class:`.Path`
    :param requirements: Path to a file containing project requirements, defaults to None
    :type requirements: :pu:class:`.Path`, optional
    :return:
    """
    with open(Path(output_file).absolute(), "w", encoding="utf-8") as outfile:
        project = RecursiveParser(Path(project_root_dir).absolute())
        project.parse_project_dir(Path(root_file).absolute())

        if requirements:
            with open(requirements, "r", encoding="utf-8") as reqs:
                project.requirements = [x for x in reqs.read().split("\n") if x]
        # TODO: we need other formats, not only json?
        json.dump(nx.readwrite.node_link_data(project.to_graph()), outfile, indent=4)


def dict2py(
    dictionary: dict,
    extract_to_directory: Path,
    process_element: str = "disambiguate",
):
    """Extract a project from a dictionary to a directory

    :param dictionary: Dictionary as one returned by :py:meth:`.RecursiveParser.to_dict`
    :param extract_to_directory: Path to a directory to extract files to
    :param process_element: Name of the function used to process dictionary elements
    :return: None
    """
    namespaces = dictionary.get("namespaces")
    requirements = dictionary.get("requirements")
    if not namespaces:
        raise DictStructureError("No namespaces found")
    if requirements is None:
        raise DictStructureError("No requirements found")

    for namespace in namespaces:
        path = namespace.split(".")
        path_to_file = Path(extract_to_directory).absolute().joinpath(*path[:-1])
        if not path_to_file.exists():
            path_to_file.mkdir(parents=True, exist_ok=True)
        path_to_file = path_to_file / (str(path[-1]) + ".py")
        if path_to_file.exists():
            logging.warning("File %s already exists", path_to_file)

        with open(path_to_file, "w", encoding="utf-8") as outfile:
            dict_processor = DictProcessor()
            dict_processor.process_element = dict_processor.__getattribute__(process_element)
            for name, value in namespaces[namespace].items():
                if isinstance(value, (Import, From)):
                    outfile.write(repr(value) + f" as {name}\n")
                elif isinstance(value, Call):
                    dict_processor.replace_lists_with_tuples = True
                    for arg in value.args:
                        value.args[arg] = dict_processor(value.args[arg])
                    outfile.write(f"{name} = {repr(value)}\n")
                    dict_processor.replace_lists_with_tuples = False
                else:
                    dict_processor.replace_lists_with_tuples = False
                    outfile.write(f"{name} = {dict_processor(value)}\n")

                dict_processor.add_name(name)
        format_file_in_place(path_to_file, fast=False, mode=FileMode(), write_back=WriteBack.YES)
    with open(extract_to_directory / "requirements.txt", "w", encoding="utf-8") as reqs:
        reqs.write("\n".join(requirements))


def yaml2py(
    yaml_file: Path,
    extract_to_directory: Path,
):
    """Extract project from a yaml file to a directory

    :param yaml_file: Yaml file to extract from
    :type yaml_file: :py:class:`.Path`
    :param extract_to_directory: Directory to extract to
    :type extract_to_directory: :py:class:`.Path`
    :return: None
    """
    with open(Path(yaml_file).absolute(), "r", encoding="utf-8") as infile:
        processed_file = yaml_dumper_loader.load(infile)
    dict2py(processed_file, extract_to_directory)


def graph2py(
    graph_file: Path,
    extract_to_directory: Path,
):
    """Extract project from a graph file to a directory

    :param graph_file: Graph file to extract from
    :type graph_file: :py:class:`.Path`
    :param extract_to_directory: Directory to extract to
    :type extract_to_directory: :py:class:`.Path`
    :return: None
    """
    with open(Path(graph_file).absolute(), "r", encoding="utf-8") as infile:
        processed_file = json.load(infile)
    graph: nx.MultiDiGraph = nx.readwrite.node_link_graph(processed_file)
    dp = DictProcessor()
    dp.process_element = dp.from_yaml
    dict2py(dp(graph.graph["script"]), extract_to_directory)
