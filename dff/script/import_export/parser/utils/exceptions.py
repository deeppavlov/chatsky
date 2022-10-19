"""This module contains different exceptions that might be raised during parsing
"""


class ParserError(Exception):
    """Raised during parsing."""


class WrongFileStructureError(ParserError):
    """Raised when a file cannot be parsed due to having elements that are not supported by the parser."""


class StarredError(ParserError):
    """Raised when star notation is used in the code."""


class ModuleNotFoundParserError(ParserError):
    """Raised when a module imported in a file being parsed is not found."""


class ResolutionError(ParserError):
    """Raised when a string cannot be cast to :py:class:`dff.script.import_export.parser.utils.namespaces.Request`."""


class ObjectNotFoundError(ResolutionError):
    """Raised when a string cannot be cast to :py:class:`dff.script.import_export.parser.utils.namespaces.Request`
    due to the string referencing an object that does not exist.
    """


class NamespaceNotParsedError(ResolutionError):
    """Raised when a string cannot be cast to :py:class:`dff.script.import_export.parser.utils.namespaces.Request`
    due to the string referencing an object in one of the namespaces that have not been parsed.
    """


class RequestParsingError(ResolutionError):
    """Raised when a string cannot be cast to :py:class:`dff.script.import_export.parser.utils.namespaces.Request`
    due to the string not being of the required format.
    """


class ScriptValidationError(ParserError):
    """Raised when :py:class:`dff.core.engine.core.actor.Actor` is initialized incorrectly."""


class KeyNotFoundError(ScriptValidationError):
    """Raised when :py:class:`dff.core.engine.core.actor.Actor` is initialized incorrectly:
    ``start_label`` or ``fallback_label`` refers to a key that does not exist in a dictionary.
    """


class DictStructureError(ParserError):
    """Raised when a dictionary does not have a correct structure"""
