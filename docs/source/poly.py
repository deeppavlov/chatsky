from pathlib import Path
from datetime import datetime
from functools import partial
from sphinx_polyversion import *
from sphinx_polyversion.git import *
from sphinx_polyversion.git import closest_tag
from sphinx_polyversion.pyvenv import Poetry
from docs.source.builder import ChatskySphinxBuilder
from docs.source.switcher_gen import generate_switcher
import git
import os

# Generate switcher.json file
generate_switcher()

# Regex matching the branches to build docs for
# This regex stands for all branches except master, so docs can be built for any branch on demand.
# (if the workflow is launched from it)
BRANCH_REGEX = r"((?!master).)*"
# BRANCH_REGEX = r".*"

#: Regex matching the tags to build docs for
TAG_REGEX = r"-"
# TODO: Make a regexp for all tags except those that include "dev, rc1 and so on"
# r""
# Basically, only leave those that fit v'number'.'number'.'number' and >= than v0.6.4
# All those "rc1" and so on should be excluded.
# It's possible to just make a really long string with the right tags.
# (could be all tags after a certain tag in the 'repo.tags' array)
# It's very quick to do, but a regexp sounds cooler.

# If 'True', builds only the latest tag. Otherwise, all tags will be built.
# TODO: (Optional, not critical) set this to 'True' if 'conf.py' hasn't changed since
# TODO: the previous version(tag).
# I'm not sure how to do it right now.
build_only_latest_tag = False

# This variable is set to `False` during workflow build. It is 'True' during local builds.
LOCAL_BUILD = os.getenv('LOCAL_BUILD', default="True")

repo = git.Repo('./')
# This variable is needed for passing the branch name during PR workflow doc builds,
# because in those cases 'repo.active_branch' gives 'detached HEAD'.
branch = os.getenv('BRANCH_NAME', default=None)
if branch is None:
    branch = repo.active_branch

if str(branch) == "master":
    if build_only_latest_tag:
        # TODO: Check for release candidates. "rc1" and don't let them through.
        # Releases are handled here (pushes into master mean a release, so the latest tag is built)
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
        latest_tag = tags[-1]
        TAG_REGEX = str(latest_tag)
    # else the default option happens - building all tags from v1.0 and beyond, I think.
    # Or whatever the user has set to the tags section.
else:
    BRANCH_REGEX = str(branch)
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
    ],
    "current": GitRef("local", "", "", GitRefType.BRANCH, datetime.fromtimestamp(2)),
}
MOCK = False

# Load overrides read from commandline to global scope
apply_overrides(globals())

# Determine repository root directory
root = Git.root(Path(__file__).parent)
src = Path(SOURCE_DIR)

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
    builder=ChatskySphinxBuilder(src, args=SPHINX_ARGS),
    env=Poetry.factory(args=POETRY_ARGS),
    selector=partial(closest_tag, root),
    template_dir=root / src / "templates",
    static_dir=root / src / "static",
    mock=MOCK_DATA,
).run(MOCK)
