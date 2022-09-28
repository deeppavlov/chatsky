"""This module contains functions that don't serve any particular purpose
"""
import re
from pathlib import Path
import typing as tp

import libcst as cst


# TODO: can `evaluate` be named more explicitly?
def evaluate(node: tp.Union[cst.CSTNode, str]) -> str:
    """Get string representation of :py:class:`libcst.CSTNode`

    :param node: Node to evaluate.
    :type node: :py:class:`libcst.CSTNode` | str
    :return: String representing node
    :rtype: str
    """
    if isinstance(node, str):
        return node
    return cst.parse_module("").code_for_node(node)


def enquote_string(string: str) -> str:
    """Enquote a string

    Return a string with all newlines, whitespaces and tabulations deleted.
    Escape single quotes inside the string.
    Wrap the string in single quotes

    :param string: String to enquote
    :type string: str
    :return: Enquoted string
    :rtype: str
    """
    return "'" + re.sub(r"\n[ \t]*", "", string).replace("'", r"\'") + "'"


def remove_suffix(target: str, suffix: str) -> str:
    """The same as a built-in :py:meth:`str.removesuffix`

    :param target: A string to remove suffix from
    :param suffix: A suffix to remove
    :return: A string  without a suffix
    """
    if target.endswith(suffix):
        return target[: -len(suffix)]
    return target


def get_module_name(path: Path, project_root_dir: Path) -> str:
    """Get a string that would be used to import a file inside a directory

    :param path: File that would be imported
    :type path: :py:class:`pathlib.Path`
    :param project_root_dir: Directory inside which the import would happen
        If ``project_root_dir`` contains __init__.py then parent directory of ``project_root_dir`` is used instead
    :type project_root_dir: :py:class:`pathlib.Path`
    :return: String that would be used to import ``path`` inside ``project_root_dir``.
    :rtype: str
    :raises :py:exc:`ValueError`:
        If ``path`` is not inside ``project_root_dir``
    :raises :py:exc:`RuntimeError`:
        If ``path`` is equal to ``project_root_dir``
    """
    if Path(project_root_dir / "__init__.py").exists():
        project_root_dir = project_root_dir.parent
    path = Path(remove_suffix(str(path), ".py"))
    # if str(path).endswith("__init__"):
    #     path = path.parent
    parts = path.relative_to(project_root_dir).parts
    if len(parts) == 0:
        raise RuntimeError(f"Parts are empty with path={path} and project_root_dir={project_root_dir}")
    return ".".join(parts)
