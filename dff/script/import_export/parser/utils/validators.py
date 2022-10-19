"""This module contains functions that make sure parsed files are correct
"""
import re
import typing as tp

import libcst as cst
from dff.core.engine.core.keywords import Keywords  # type: ignore

from dff.script.import_export.parser.utils.code_wrappers import StringTag, Python
from dff.script.import_export.parser.utils.convenience_functions import repr_libcst_node
from dff.script.import_export.parser.utils.exceptions import WrongFileStructureError, ScriptValidationError
from dff.script.import_export.parser.utils.namespaces import Call

if tp.TYPE_CHECKING:
    from dff.script.import_export.parser.processors.recursive_parser import RecursiveParser

keywords_dict = {
    k: [Python(k, "dff.core.engine.core.keywords." + k), Python(k, "dff.core.engine.core.keywords.Keywords." + k)]
    for k in Keywords.__members__
}

keywords_list = list(map(lambda x: Python(x, "dff.core.engine.core.keywords." + x), Keywords.__members__)) + list(
    map(lambda x: Python(x, "dff.core.engine.core.keywords.Keywords." + x), Keywords.__members__)
)


def check_file_structure(
    node: cst.CSTNode,
) -> None:
    """Check that node is empty.

    The `dff.script.import_export.parser.processors.parse.Parse` removes supported nodes.
    This function makes sure that there are no unsupported nodes in a file by checking that the resulting node is empty

    :param node: Node to check
    :type node: :py:class:`libcst.CSTNode`

    :raise :py:exc:`dff.script.import_export.parser.utils.exceptions.WrongFileStructureError`:
        If the node is not empty. Message includes the first unsupported line of code.
    """
    remaining_file = repr_libcst_node(node)

    if re.fullmatch(r"[ \t\n\r]*", remaining_file) is None:
        first_non_empty_line = next(line for line in remaining_file.split("\n") if line)
        raise WrongFileStructureError(
            f"""File must contain only imports, dict declarations and function calls.
            The first line of other type found: {first_non_empty_line}"""
        )


def validate_path(
    traversed_path: tp.List[StringTag],
    final_value: tp.Union[StringTag, Call],
    paths: tp.List[tp.List[str]],
    project: "RecursiveParser",
) -> None:
    """Validate a sequence of keys in a script.

    When a script tree is traversed during checking in
    :py:meth:`dff.script.import_export.parser.processors.recursive_parser.RecursiveParser.traverse_dict`
    this function is called at the leaf nodes

    :param traversed_path: Sequence of tree nodes visited before the leaf node
    :type traversed_path:
        tuple[
        :py:class:`dff.script.import_export.parser.utils.code_wrappers.Python`,
        :py:class:`dff.script.import_export.parser.utils.code_wrappers.String`
        ]
    :param final_value: Value of the leaf node, defaults to None
    :type final_value:
        :py:class:`dff.script.import_export.parser.utils.code_wrappers.Python`
        |
        :py:class:`dff.script.import_export.parser.utils.code_wrappers.String`,
        optional
    :param paths: Path to the ``value``
    :type paths: list[str]

    :raises :py:exc:`dff.script.import_export.parser.utils.exceptions.ScriptValidationError`:

        - If ``traversed_path`` is empty
        - If the first element of ``traversed_path`` is :py:obj:`dff.core.engine.core.keywords.GLOBAL` but the second
          element does not exist or is not in :py:mod:`dff.core.engine.core.keywords`
        - If the first element of ``traversed_path`` is not :py:obj:`dff.core.engine.core.keywords.GLOBAL` but the third
          element does not exist or is not in :py:mod:`dff.core.engine.core.keywords`
    """
    if len(traversed_path) < 1:
        raise ScriptValidationError(f"No keys in a traversed path.\n" f"Keys point to: {final_value}")
    if project.resolve_name(traversed_path[0]) in keywords_dict["GLOBAL"]:
        if len(traversed_path) < 2:
            raise ScriptValidationError(
                f"Less than 2 consecutive keys in a script: {traversed_path}.\n" f"Keys point to: {final_value}"
            )
        if project.resolve_name(traversed_path[1]) not in keywords_list:
            raise ScriptValidationError(f"GLOBAL keys should be keywords: {traversed_path}")
    else:
        if len(traversed_path) < 3:
            raise ScriptValidationError(
                f"Less than 3 consecutive keys in a script: {traversed_path}.\n" f"Keys point to: {final_value}"
            )
        if project.resolve_name(traversed_path[2]) not in keywords_list:
            raise ScriptValidationError(f"Node keys should be keywords: {traversed_path}")
