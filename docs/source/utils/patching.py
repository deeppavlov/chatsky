from hashlib import sha256
from logging import INFO, getLogger, StreamHandler
from typing import Callable, Optional, Any
from inspect import signature, getsourcefile, getsourcelines

from sphinx.ext.autosummary import extract_summary
from nbsphinx import depart_gallery_html
import sphinx_autodoc_typehints

logger = getLogger(__name__)
logger.addHandler(StreamHandler())
logger.setLevel(INFO)


def patch_source_file(module: str, patch: str, patch_payload: Optional[str] = None) -> bool:
    """
    Patch library source file.
    New code is appended to the library source code file, so use it in `venv` only!
    Function can be called multiple times, it won't re-apply the same patches.

    :param module: Module name (file name) to apply the patch to. Should be writable.
    :type module: str
    :param patch: Python source code to append (a.k.a. patch).
    :type patch: str
    :param patch_payload: Unique patch identifier string (used to prevent patch re-applying).
        If not provided, `patch` string will be used for identification instead.
    :type patch_payload: str, optional
    :return: True if patch was applied, False if the file is already patched before.
    :rtype: bool
    """
    patch_payload = patch if patch_payload is None else patch_payload
    patch_comment = f"# Patched with: {sha256(patch_payload.encode('utf-8')).hexdigest()}"
    patch = f"\n\n\n{patch_comment}\n{patch}\n"
    with open(module, "r") as file:
        if any(patch_comment in line for line in file.readlines()):
            return False
    with open(module, "a") as file:
        file.write(patch)
    return True


def wrap_source_function(source: Callable, wrapper: Callable[[Callable], Any]):
    """
    Wrap library function.
    Works just like `patch_source_file`.
    Has some limitations on library and wrapper functions (should be customized for your particular case).
    Let library function name be `[source]`, then:
    1. Library file should NOT have functions called `[source]_wrapper` and `[source]_old`.
       Otherwise, these functions will be overwritten and unavailable.
    2. Wrapper function shouldn't have type hints that are not defined in the library file.
       No imports are added along with patch function, and its definition and code is copied literally.
    3. Wrapper function shouldn't have neither docstring nor multiline definition.
       Its definition is considered to be (and is copied as) single line,
       anything starting from the second line should be code.

    :param source: Library function to wrap (exported from the module patch will be applied to).
    :type source: callable
    :param wrapper: Wrapper function, should accept `source`
        function as single parameter and return whatever it returns.
    :type wrapper: callable
    """
    src_file = getsourcefile(source)
    src_name = getattr(source, "__name__")
    logger.info(f"Wrapping function '{src_name}'...")
    wrap_body = "".join(getsourcelines(wrapper)[0][1:])
    wrap_sign = f"def {src_name}_wrapper{signature(wrapper)}"
    patch = f"{src_name}_old = {src_name}\n{wrap_sign}:\n{wrap_body}\n{src_name} = {src_name}_wrapper({src_name}_old)"
    if patch_source_file(src_file, patch, patch_payload=f"{signature(wrapper)}:\n{wrap_body}"):
        logger.info("Function wrapped successfully!")
    else:
        logger.info("Function already wrapped, skipping.")


# And here are our patches:


def extract_summary_wrapper(func):
    return lambda doc, document: func(doc, document).split("\n\n")[-1]


def depart_gallery_html_wrapper(func):
    def wrapper(self, node):
        entries = node["entries"]
        for i in range(len(entries)):
            entries[i] = list(entries[i])
            title_split = entries[i][0].split(": ")
            entries[i][0] = entries[i][0] if len(title_split) == 1 else title_split[-1]
        return func(self, node)

    return wrapper


if __name__ == "__main__":
    wrap_source_function(extract_summary, extract_summary_wrapper)
    wrap_source_function(depart_gallery_html, depart_gallery_html_wrapper)
    patch_source_file(
        getsourcefile(sphinx_autodoc_typehints),
        """
class LoggerDummy():
    def warning(self, message, *args):
        print(f"Warning suppressed: {message % args}")

_LOGGER = LoggerDummy()
""",
    )
