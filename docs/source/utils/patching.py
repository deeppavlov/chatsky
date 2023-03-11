from hashlib import sha256
from logging import INFO, getLogger, StreamHandler
from typing import Callable, Optional
from inspect import signature, getsourcefile, getsourcelines

from sphinx.ext.autosummary import extract_summary

logger = getLogger(__name__)
logger.addHandler(StreamHandler())
logger.setLevel(INFO)


def _get_body(func: Callable):
    """
    Using the magic method __doc__, we KNOW the size of the docstring.
    We then, just subtract this from the total length of the function.
    """
    try:
        lines_to_skip = len(getattr(func, "__doc__").split("\n")) + 1
    except AttributeError:
        lines_to_skip = 1
    return "".join(getsourcelines(func)[0][lines_to_skip:])


def patch_source_file(module: str, patch: str, patch_payload: Optional[str] = None) -> bool:
    patch_payload = patch if patch_payload is None else patch_payload
    patch_comment = f"# Patched with: {sha256(patch_payload.encode('utf-8')).hexdigest()}"
    patch = f"\n\n\n{patch_comment}\n{patch}\n"
    with open(module, "r") as file:
        if any(patch_comment in line for line in file.readlines()):
            return False
    with open(module, "a") as file:
        file.write(patch)
    return True


def wrap_source_function(source: Callable, wrapper: Callable):
    src_file = getsourcefile(source)
    src_name = getattr(source, "__name__")
    logger.info(f"Wrapping function '{src_name}'...")
    wrap_body = _get_body(wrapper)
    wrap_sign = f"def {src_name}_wrapper{signature(wrapper)}"
    patch = f"{src_name}_old = {src_name}\n{wrap_sign}:\n{wrap_body}\n{src_name} = {src_name}_wrapper({src_name}_old)"
    if patch_source_file(src_file, patch, patch_payload=f"{signature(wrapper)}:\n{wrap_body}"):
        logger.info("Function wrapped successfully!")
    else:
        logger.info("Function already wrapped, skipping.")


# And here are our patches:


def extract_summary_wrapper(func):
    return lambda doc, document: func(doc, document).split("\n\n")[-1]


if __name__ == '__main__':
    wrap_source_function(extract_summary, extract_summary_wrapper)
