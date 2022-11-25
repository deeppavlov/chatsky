class BaseParserException(BaseException):
    ...


class ResolutionError(BaseParserException):
    """
    Raised during name resolution
    """
    ...


class KeyNotFound(ResolutionError):
    """
    Raised when a key is not found
    """
    ...


class StarError(BaseParserException):
    """
    Raised when star notation is used
    """
    ...
