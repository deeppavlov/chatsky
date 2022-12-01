class BaseParserException(BaseException):
    ...


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
