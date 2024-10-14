import re
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

#: Regex matching the tags to build docs for (will get overwritten without the option below)
TAG_REGEX = r"-"
# You can set this to 'True' to run default sphinx-polyversion with few changes of our own.
custom_tag_regex = False

# Add an env variable from GitHub Actions, maybe.
first_built_version = "v0.8.0"

# If 'True', builds only the latest tag. Otherwise, all tags will be built.
# TODO: (Optional, not critical) set this to 'True' if 'conf.py' hasn't changed since
# the previous version(tag). I'm not sure how to do it right now.
build_only_latest_tag = False

# This variable is set to `False` during workflow build. It is 'True' during local builds.
LOCAL_BUILD = os.getenv('LOCAL_BUILD', default="True")

repo = git.Repo('./')
# This variable is needed for passing the branch name during PR workflow doc builds,
# because in those cases 'repo.active_branch' gives 'detached HEAD'.
branch = os.getenv('BRANCH_NAME', default=None)
if branch is None:
    branch = repo.active_branch


# This makes sure that tags which include 'rc' and 'dev' strings aren't built for the latest tag option.
# Is this a good thing, actually?
# TODO: discuss this.
def find_latest_tag(tag_list: list):
    latest_tag = tag_list[-1]
    shift = 0
    while "rc" in latest_tag or "dev" in latest_tag:
        shift += 1
        latest_tag = tag_list[-shift]
    return latest_tag


# Filter func for building latest versions of each major tag.
# Returns a dictionary of major tag groups as keys and latest tag's number as values
# e.g. {(0, 6): 7, (1, 2): 3} standing for v0.6.7 and v1.2.3.
def latest_tags_filter(tag_list: list):
    regex = re.compile(r"^v\d*\.\d*\.\d*$")
    tag_list = list(filter(regex.match, tag_list))
    latest_tags = {}
    for tag in tag_list:
        tag = str(tag).replace('v', '').split(".")
        tag_group = (tag[0], tag[1])
        # Not building versions lower than v0.8.0
        if not (int(tag[0]) == 0 and int(tag[1]) < 8):
            # If there is a greater tag in this group, it will have priority over others
            if int(tag[2]) > int(latest_tags.get(tag_group, -1)):
                latest_tags[tag_group] = tag[2]
    # Could return a dictionary, but it looks unclear.
    tag_list = ['v' + x[0] + '.' + x[1] + '.' + latest_tags[x] for x in latest_tags.keys()]
    return tag_list


def create_tag_regex(tag_list: list):
    # Maybe could add a 'start_version' for building
    start_index = tag_list.index(first_built_version)
    tag_list = tag_list[start_index:]
    # Filter for latest tags in their respective groups
    tag_list = latest_tags_filter(tag_list)
    # Creates the regex
    tag_regex = r"("
    for tag in tag_list:
        tag_regex += str(tag) + "|"
    tag_regex = tag_regex[:-1] + ")"
    return tag_regex


print(branch)
if str(branch) == "master":
    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    tags = [str(x) for x in tags]
    print(tags)
    if build_only_latest_tag:
        # Releases are handled here (pushes into master mean a release, so the latest tag is built)
        TAG_REGEX = str(find_latest_tag(tags))
    # If v0.8.0 is not in tags there's something wrong, this line is quite wrong,
    # but for now it makes sure docs don't crash in case someone fetches only a part of tags
    elif first_built_version in tags and not custom_tag_regex:
        TAG_REGEX = create_tag_regex(tags)
else:
    BRANCH_REGEX = str(branch)
    TAG_REGEX = r"-"
print("TAG_REGEX = ", TAG_REGEX)

#: Output dir relative to project root
OUTPUT_DIR = "docs/build"

#: Source directory
SOURCE_DIR = "docs/source"

# Could attempt adding "--sync", but seems like an awful solution, even if it works
# Really should to add the latest version of sphinx-polyversion programmatically.
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
