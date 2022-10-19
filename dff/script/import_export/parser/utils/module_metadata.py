"""This module contains functions that retrieve module metadata
"""
import importlib.util
import json
import logging
import typing as tp
from enum import Enum
from pathlib import Path

import pkg_resources
from isort import place_module

from dff.script.import_export.parser.utils.exceptions import ModuleNotFoundParserError


class ModuleType(Enum):
    """Types of modules being imported in a script

    Enums:

    PIP: "pip"
        used for modules that are available via pip such as :py:mod:`dff.core.engine`

    SYSTEM: "system"
        used for modules listed in :py:data:`sys.stdlib_module_names` such as :py:mod:`sys`

    LOCAL: "local:
        used for other modules
    """

    PIP = "pip"
    SYSTEM = "system"
    LOCAL = "local"


def get_distribution_metadata(
    module_name: str,
) -> tp.Optional[str]:
    """Get metadata of a :py:attr:`ModuleType.PIP` distribution

    :param module_name: Module name
    :type module_name: str

    :return: Distribution metadata:

        - For distributions installed via VCS: ``"{vcs}+{url}@{commit}"``
        - For distributions installed via pypi: ``"{project_name}=={version}"``
        - None otherwise

    :rtype: str, optional
    """
    # find distribution
    try:
        dist = pkg_resources.get_distribution(module_name)
    except pkg_resources.DistributionNotFound as error:
        logging.debug("%s: %s\nparams:\nmodule=%s", type(error), error, module_name)
        return None

    # find VCS info
    try:
        vcs_info = json.load((Path(dist.egg_info) / "direct_url.json").open("r"))  # type: ignore
        return f"{vcs_info['vcs_info']['vcs']}+{vcs_info['url']}@{vcs_info['vcs_info']['commit_id']}"
    except (
        AttributeError,
        FileNotFoundError,
        json.decoder.JSONDecodeError,
        KeyError,
    ) as error:
        logging.debug("%s: %s\nparams:\nmodule=%s", type(error), error, module_name)

    # find distribution pypi info
    try:
        return f"{dist.project_name}=={dist.version}"
    except AttributeError as error:
        logging.debug("%s: %s\nparams:\nmodule=%s", type(error), error, module_name)
    return None


def get_local_module_location(
    module_name: str,
    inside_dir: tp.Union[str, Path],
) -> tp.Optional[str]:
    """Get location of a :py:attr:`ModuleType.LOCAL` module

    :param module_name: Module name
    :type module_name: str
    :param inside_dir: Parent directory of a script that is importing the module
    :type inside_dir: str | :py:class:`pathlib.Path`

    :return: Location of the module
    :rtype: str, optional
    """
    # for some reason importlib did not work correctly with relative import so write our own function
    directory = Path(inside_dir).absolute()

    if not module_name.startswith("."):
        module_name = "." + module_name

    found_non_empty = False
    # this variable tracks if we have encountered a non-empty element in ``dot_split``
    dot_split = module_name[1:].split(".")
    # split the module name by ".". The first character is always ".".
    for string in dot_split[:-1]:

        if found_non_empty and string == "":
            raise ModuleNotFoundParserError(f"Using double dots after module name is not allowed: {module_name}")

        if string == "":
            if directory == directory.root:
                raise ModuleNotFoundParserError(
                    f"Importing {module_name} inside {inside_dir} refers to a file outside {directory.root}."
                )
            directory = directory.parent

        else:
            found_non_empty = True
            directory = directory / string

    # there are two possibilities when we import "file":
    # we either import "file.py" or "file/__init__.py"
    file1 = directory / dot_split[-1] / "__init__.py"
    file2 = directory / (dot_split[-1] + ".py")
    if file1.exists() and file2.exists():
        logging.warning("Found two files with the same name: %s; %s", file1, file2)
        # return file 1 but also warn user
    if file1.exists():
        return str(file1.absolute())
    if file2.exists():
        return str(file2.absolute())
    return None


def get_other_module_location(
    module_name: str,
) -> tp.Optional[str]:
    """Get location of a :py:attr:`ModuleType.PIP` or :py:attr:`ModuleType.SYSTEM` module. Used to check that
    a submodule of a module exists

    :param module_name: Module name
    :type module_name: str

    :return: Location of the module
    :rtype: str, optional
    """
    try:
        spec = importlib.util.find_spec(module_name)

        if spec is None:
            return None
        return spec.origin
    except ModuleNotFoundError as error:
        logging.debug("%s: %s\nparams:\nmodule=%s", type(error), error, module_name)
        return None


def get_module_info(
    module_name: str,
    inside_dir: tp.Union[str, Path],
) -> tp.Tuple[ModuleType, str]:
    """Get information about module

    :param module_name: Name of the module
    :type module_name: str
    :param inside_dir: Parent directory of the script that imports the module
    :type inside_dir: str | :py:class:`pathlib.Path`

    :raises :py:exc:`dff.script.import_export.parser.utils.exceptions.ModuleNotFoundParserError`:
        If the module is not found with the specified params

    :return: A tuple of two elements. The first one is a :py:class:`ModuleType` instance. The second one is:

        - result of :py:func:`get_distribution_metadata` if the first element is :py:attr:`ModuleType.PIP`
        - name of the root module if the first element is :py:attr:`ModuleType.SYSTEM`
        - result of :py:func:`get_local_module_location` if the first element is :py:attr:`ModuleType.LOCAL`
    :rtype: tuple[:py:class:`ModuleType`, str]
    """
    root_module = module_name.split(".")[0]

    if root_module != "":
        package_metadata = get_distribution_metadata(root_module)
        if package_metadata is not None and get_other_module_location(module_name) is not None:
            return ModuleType.PIP, package_metadata

        if place_module(root_module) == "STDLIB" and get_other_module_location(module_name) is not None:
            return ModuleType.SYSTEM, root_module

    location = get_local_module_location(module_name, inside_dir)

    if location is None:
        raise ModuleNotFoundParserError(f"Not found {module_name} in {inside_dir}")

    return ModuleType.LOCAL, str(Path(location).absolute())
