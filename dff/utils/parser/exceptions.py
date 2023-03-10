class BaseParserException(BaseException):
    ...


class ScriptValidationError(BaseParserException):
    """
    Raised during script validation
    """


class ParsingError(BaseParserException):
    """
    Raised during parsing
    """


class ResolutionError(BaseParserException):
    """
    Raised during name resolution
    """

    ...


# todo: add support for star notation
class StarError(BaseParserException):
    """
    Raised when star notation is used
    """

    ...
