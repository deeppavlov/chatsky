class BaseParserException(BaseException):
    ...


class ResolutionError(BaseParserException):
    """
    Raised during name resolution
    """
    ...


class StarError(BaseParserException):
    """
    Raised when star notation is used
    """
    ...
