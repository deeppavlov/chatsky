from pathlib import Path
from datetime import datetime
from sphinx_polyversion import *
from sphinx_polyversion.git import *
from sphinx_polyversion.pyvenv import Poetry
from sphinx_polyversion.sphinx import SphinxBuilder

#: Regex matching the branches to build docs for
BRANCH_REGEX = r"(dev|master|test_branch|test_branch_2|feat/sphinx_multiversion|sphinx_multiversion_test)"

#: Regex matching the tags to build docs for
TAG_REGEX = r"-"

#: Output dir relative to project root
OUTPUT_DIR = "docs/build"

#: Source directory
SOURCE_DIR = "docs/source"

#: Arguments to pass to `poetry install`
POETRY_ARGS = "--with tutorials,docs --all-extras --no-ansi --no-interaction".split()

#: Arguments to pass to `sphinx-build`
SPHINX_ARGS = "-b html -W --keep-going -v".split()

#: Mock data used for building local version
MOCK_DATA = {
    "revisions": [
        GitRef("dev", "", "", GitRefType.BRANCH, datetime.fromtimestamp(0)),
        GitRef("master", "", "", GitRefType.BRANCH, datetime.fromtimestamp(1)),
        GitRef("test_branch", "", "", GitRefType.BRANCH, datetime.fromtimestamp(2)),
        GitRef("test_branch_2", "", "", GitRefType.BRANCH, datetime.fromtimestamp(3)),
        GitRef("feat/sphinx_multiversion", "", "", GitRefType.BRANCH, datetime.fromtimestamp(4)),
    ],
    "current": GitRef("local", "", "", GitRefType.BRANCH, datetime.fromtimestamp(5)),
}
MOCK = False

# Load overrides read from commandline to global scope
apply_overrides(globals())
# Determine repository root directory
root = Git.root(Path(__file__).parent)

# Debug (Delete before PR!)
src = Path(SOURCE_DIR)
vcs_test=Git(
    branch_regex=BRANCH_REGEX,
    tag_regex=TAG_REGEX,
    buffer_size=1 * 10**9,  # 1 GB
    predicate=file_predicate([src]), # exclude refs without source dir
),
# print(vcs_test.retrieve(root))
# Setup driver and run it
DefaultDriver(
    root,
    OUTPUT_DIR,
    vcs=Git(
        branch_regex=BRANCH_REGEX,
        tag_regex=TAG_REGEX,
        buffer_size=1 * 10**9,  # 1 GB
        predicate=file_predicate([src]), # exclude refs without source dir
    ),
    builder=SphinxBuilder(src, args=SPHINX_ARGS),
    env=Poetry.factory(args=POETRY_ARGS),
    template_dir=root / src / "templates",
    static_dir=root / src / "static",
    mock=MOCK_DATA,
).run(MOCK)
