import os

import git
import json
from docs.source.utils.tags_filter import latest_tags_filter


def generate_switcher():
    # TODO: add a parameter with github actions (env)
    # Parameters that say start_version and a black_list_regex, also a whitelist in case latest_tag
    # is actually relevant and should also be built.

    # TODO: Discuss the following:
    # The parameters exist now, but they're done as an env sort of variables.
    # How should they be used?
    blacklisted_tags = os.getenv("VERSION_SWITCHER_TAG_BLACKLIST", default=[])
    whitelisted_tags = os.getenv("VERSION_SWITCHER_TAG_WHITELIST", default=[])
    # Retrieve and filter git tags
    repo = git.Repo('./')

    tags = [str(x) for x in repo.tags]
    tags = latest_tags_filter(tags)
    for tag in tags:
        if tag in blacklisted_tags:
            tags.remove(tag)
    for tag in whitelisted_tags:
        if tag not in tags:
            tags.append(tag)

    # Sort the tags for the version switcher button.
    tags.sort(key=lambda x: x.replace('v', '').split("."))
    tags.reverse()

    # TODO: Could add 'preferred' back in / remove it, but there are issues to be solved in that case.
    # Like, it will say that 'dev' is bad / outdated, because it's not the 'preferred' version.
    # Well, it could be useful for new users, seeing a bright red banner if they're using 'dev'
    # when they didn't really need it.
    switcher_json = []

    # TODO: Ensure that 'master' is renamed to 'latest' in the docs.
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
