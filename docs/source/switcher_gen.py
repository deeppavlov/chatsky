import os

import git
import json
from docs.source.utils.tags_filter import latest_tags_filter


# TODO: Redo this entire thing - sort through tags to find the ones which are going to be built
#  or get the funcs from poly.py do it. Also find the latest tag,
#  it must be renamed to "latest(v0.9.0)" or something like that.
# Yeah, I should be just renaming 'master' to 'latest'.
# Although, specifying the version would be nice. Actually, its a good question, I can't just write 'latest'
# Without any version after it, right?
def generate_switcher():
    # TODO: add a parameter with github actions (env)
    # Parameters that say start_version and a black_list_regex, also a whitelist in case latest_tag
    # is actually relevant and should also be built.

    # The parameter exists now, but it's done as an env sort of variable.
    # How should it be used?
    blacklisted_tags = os.getenv("VERSION_SWITCHER_TAG_BLACKLIST", default=[])
    whitelisted_tags = os.getenv("VERSION_SWITCHER_TAG_WHITELIST", default=[])
    # retrieving and filtering git tags
    repo = git.Repo('./')

    tags = [str(x) for x in repo.tags]
    tags = latest_tags_filter(tags)
    for tag in tags:
        if tag in blacklisted_tags:
            tags.remove(tag)
    for tag in whitelisted_tags:
        if tag not in tags:
            tags.append(tag)

    tags = [str(tag).replace('v', '').split(".") for tag in tags]
    # I assume there are no version numbers higher than 100, then it's all correct.
    # I just thought this is an interesting solution. But yeah, this just seems illegal.
    # TODO: use a conventional solution for this, maybe there is something built-in?
    tags = sorted(tags, key=lambda t: 1000000 * t[0] + 1000 * t[1] + t[2])
    tags = ['v' + x[0] + '.' + x[1] + '.' + x[2] for x in tags]

    # TODO: Maybe remove 'preferred' completely?
    # Otherwise, it will say that 'dev' is bad / outdated, I'm not sure.
    switcher_json = []

    latest_data = {
        "name": "latest",
        "version": "master",
        "url": "https://deeppavlov.github.io/chatsky/master/index.html",
        "preferred": "true"
    }
    switcher_json += [latest_data]

    dev_data = {
        "version": "dev",
        "url": "https://deeppavlov.github.io/chatsky/dev/index.html",
    }
    switcher_json += [dev_data]

    for tag in tags:
        url = "https://deepavlov.github.io/chatsky/" + str(tag) + "/index.html"
        tag_data = {
            "name": str(tag),
            "version": str(tag),
            "url": url,
        }
        switcher_json += [tag_data]

    switcher_json_obj = json.dumps(switcher_json, indent=4)

    # Write nested JSON data to the switcher.json file
    with open('./docs/source/_static/switcher.json', 'w') as f:
        f.write(switcher_json_obj)
