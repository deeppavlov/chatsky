import re
import abc
from typing import ClassVar, Literal, Optional

from pydantic import BaseModel
from jupytext import jupytext


class ReplacePattern(BaseModel, abc.ABC):
    """
    An interface for replace patterns.
    """
    @property
    @abc.abstractmethod
    def pattern(self) -> re.Pattern:
        """
        A regex pattern to replace in a text.
        """
        ...

    @staticmethod
    @abc.abstractmethod
    def replacement_string(matchobj: re.Match) -> str:
        """
        Return a replacement string for a match object.

        :param matchobj: A regex match object.
        :return: A string to replace match with.
        """
        ...

    @classmethod
    def replace(cls, text: str) -> str:
        """
        Replace all instances of `pattern` in `text` with the result of `replacement_string`.

        :param text: A text in which patterns are replaced.
        :return: A string with patterns replaced.
        """
        return re.sub(cls.pattern, cls.replacement_string, text)


class InstallationCell(ReplacePattern):
    """
    Replace installation cells directives.

    Replace `# %pip install {}` with 3 py:percent cells that install dependencies and split the tutorial in parts.
    """

    pattern: ClassVar[re.Pattern] = re.compile("# %pip install (.*)\n")

    @staticmethod
    def replacement_string(matchobj: re.Match) -> str:
        return f"""# %% [markdown]
\"\"\"
__Installing dependencies__
\"\"\"

# %%
%pip install {matchobj.group(1)}

# %% [markdown]
\"\"\"
__Running tutorial__
\"\"\"
"""


class DocumentationLink(ReplacePattern):
    """
    Replace documentation linking directives.

    Replace strings of the `!doclink({args})` format with corresponding links to local files.

    `args` is a comma-separated string of arguments to pass to the :py:meth:`.DocumentationLink.link_to_doc_page`.

    So, `!doclink(arg1,arg2,arg3)` will be replaced with `link_to_doc_page(arg1, arg2, arg3)`, and
    `!doclink(arg1,arg2)` will be replaced with `link_to_doc_page(arg1, arg2)`.

    USAGE EXAMPLES
    --------------

    [link](!doclink(api,script.core.script))

    [link](!doclink(api,script.core.script,Node))

    [link](!doclink(tutorial,messengers.web_api_interface.4_streamlit_chat))

    [link](!doclink(tutorial,messengers.web_api_interface.4_streamlit_chat,API-configuration))

    [link](!doclink(guide,basic_conceptions))

    [link](!doclink(guide,basic_conceptions,example-conversational-chat-bot))

    """

    pattern: ClassVar[re.Pattern] = re.compile(r"!doclink\((.+?)\)")

    @staticmethod
    def link_to_doc_page(
        page_type: Literal["api", "tutorial", "guide"],
        page: str,
        anchor: Optional[str] = None,
    ):
        """
        Create a link to a documentation page.

        :param page_type:
            Type of the documentation:

                - "api" -- API reference
                - "tutorial" -- Tutorials
                - "guide" -- User guides

        :param page:
            Name of the page without the common prefix.

            So, to link to keywords, pass "script.core.keywords" as page (omitting the "dff" prefix).

            To link to the basic script tutorial, pass "script.core.1_basics" (without the "tutorials" prefix).

            To link to the basic concepts guide, pass "basic_conceptions".
        :param anchor:
            An anchor on the page. (optional)

            For the "api" type, use only the last part of the linked object.

            So, to link to the `CLIMessengerInterface` class, pass "CLIMessengerInterface" only.

            To link to a specific section of a tutorial or a guide, pass an anchor as-is (e.g. "introduction").
        :return:
            A link to the corresponding documentation part.
        """
        doc_prefix = ".."
        if page_type == "api":
            return f"{doc_prefix}/apiref/dff.{page}.rst" + (f"#dff.{page}.{anchor}" if anchor is not None else "")
        elif page_type == "tutorial":
            return f"{doc_prefix}/tutorials/tutorials.{page}.py" + (f"#{anchor}" if anchor is not None else "")
        elif page_type == "guide":
            return f"{doc_prefix}/user_guides/{page}.rst" + (f"#{anchor}" if anchor is not None else "")

    @staticmethod
    def replacement_string(matchobj: re.Match) -> str:
        args = matchobj.group(1).split(",")
        return DocumentationLink.link_to_doc_page(*args)


def apply_replace_patterns(text: str) -> str:
    for cls in (InstallationCell, DocumentationLink):
        text = cls.replace(text)

    return text


def py_percent_to_notebook(text: str):
    return jupytext.reads(apply_replace_patterns(text), "py:percent")
