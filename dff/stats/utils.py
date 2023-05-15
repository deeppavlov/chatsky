"""
Utils
-----
This module includes utilities designed for statistics collection.

"""
from dff.pipeline import ExtraHandlerRuntimeInfo


def get_wrapper_field(info: ExtraHandlerRuntimeInfo, postfix: str = "") -> str:
    """
    This function can be used to obtain a key, under which the wrapper data will be stored
    in the context.

    :param info: Handler runtime info obtained from the pipeline.
    :param postfix: Field-specific postfix that will be appended to the field name.
    """
    return f"{info['component']['path']}" + (f"-{postfix}" if postfix else "")
