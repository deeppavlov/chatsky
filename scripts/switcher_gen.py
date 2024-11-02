import os
import git
import json
import re


# TODO: add a first_version parameter
# Filter func for building latest versions of each major tag.
# Returns a dictionary of major tag groups as keys and latest tag's number as values
# e.g. {(0, 6): 7, (1, 2): 3} standing for v0.6.7 and v1.2.3.
def latest_tags_filter(tag_list: list) -> list:
    regex = re.compile(r"^v\d*\.\d*\.\d*$")
    tag_list = list(filter(regex.match, tag_list))
    latest_tags = {}
    for tag in tag_list:
        tag = str(tag).replace("v", "").split(".")
        tag_group = (tag[0], tag[1])
        # Not building versions lower than v0.8.0
        if not (int(tag[0]) == 0 and int(tag[1]) < 8):
            # If there is a greater tag in this group, it will have priority over others
            if int(tag[2]) > int(latest_tags.get(tag_group, -1)):
                latest_tags[tag_group] = tag[2]
    # Could return a dictionary, but it looks unclear.
    tag_list = ["v" + x[0] + "." + x[1] + "." + latest_tags[x] for x in latest_tags.keys()]
    return tag_list


def generate_version_switcher():
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
        "url": "https://zerglev.github.io/chatsky/master/",
        "preferred": "true"
    }
    switcher_json += [latest_data]

    dev_data = {
        "version": "dev",
        "url": "https://zerglev.github.io/chatsky/dev/",
    }
    switcher_json += [dev_data]

    for tag in tags:
        url = "https://zerglev.github.io/chatsky/" + str(tag) + "/"
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
