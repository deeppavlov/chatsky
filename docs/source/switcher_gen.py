import os
import git
import json
from docs.source.utils.tags_filter import latest_tags_filter


def generate_switcher():
    # TODO: add a start_version parameter with github actions (env)
    blacklisted_tags = os.getenv("VERSION_SWITCHER_TAG_BLACKLIST", default=[])
    whitelisted_tags = os.getenv("VERSION_SWITCHER_TAG_WHITELIST", default=[])
    # Retrieve and filter git tags
    repo = git.Repo('./')

    # Could maybe place the latest_tags_filter() in this file, it's only used here.
    tags = [str(x) for x in repo.tags]
    tags = latest_tags_filter(tags)

    # TODO: Consider making this look better, it's a bit hard to read.
    # Removing blacklisted tags and adding whitelisted tags.
    tags = [x for x in tags if x not in blacklisted_tags]
    tags = tags + [x for x in whitelisted_tags if x not in tags]

    # Sort the tags for the version switcher button.
    tags.sort(key=lambda x: x.replace('v', '').split("."))
    tags.reverse()

    # TODO: Could add 'preferred' back in / remove it, but there are issues to be solved in that case.
    # Like, it will say that 'dev' is bad / outdated, because it's not the 'preferred' version.
    # Well, it could be useful for new users, seeing a bright red banner if they're using 'dev'
    # when they didn't really need it.
    switcher_json = []

    # TODO: Ensure that 'master' is renamed to 'latest' in the docs.
    # TODO: (before merge) Replace all occurrences of 'zerglev' with deeppavlov! Use Ctrl+Shift+F.
    latest_data = {
        "name": "latest",
        "version": "master",
        "url": "https://zerglev.github.io/chatsky/master/index.html",
        "preferred": "true"
    }
    switcher_json += [latest_data]

    dev_data = {
        "version": "dev",
        "url": "https://zerglev.github.io/chatsky/dev/index.html",
    }
    switcher_json += [dev_data]

    for tag in tags:
        url = "https://zerglev.github.io/chatsky/" + str(tag) + "/index.html"
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
