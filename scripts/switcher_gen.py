import os
import git
import json
import re


# Filter func for building latest versions of each major tag.
# Creates a dictionary of major tag groups as keys and latest tag's number as values
# e.g. {(0, 6): 7, (1, 2): 3} standing for v0.6.7 and v1.2.3.
# Returns a list of tags right now, as it's more useful outside of this function.
def latest_tags_filter(tag_list: list, start_version: str = "v0.8.0") -> list:
    regex = re.compile(r"^v\d+\.\d+\.\d+$")
    tag_list = list(filter(regex.match, tag_list))
    latest_tags = {}
    start_version = str(start_version).replace("v", "").split(".")
    for tag in tag_list:
        tag = str(tag).replace("v", "").split(".")
        tag_group = (tag[0], tag[1])
        # Not building versions lower than v0.8.0 (or other)
        if not (int(tag[0]) == int(start_version[0]) and int(tag[1]) < int(start_version[1])):
            # If there is a greater tag in this group, it will have priority over others
            if int(tag[2]) > int(latest_tags.get(tag_group, -1)):
                latest_tags[tag_group] = tag[2]
    # Could return a dictionary, but it looks unclear.
    tag_list = ["v" + x[0] + "." + x[1] + "." + latest_tags[x] for x in latest_tags.keys()]
    return tag_list


def generate_version_switcher():
    # Retrieve GitHub Actions variables and parse them
    start_version = os.getenv("VERSION_SWITCHER_STARTING_TAG", default="v0.8.0")

    blacklisted_tags = os.getenv("VERSION_SWITCHER_TAG_BLACKLIST", default=[])
    blacklisted_tags = blacklisted_tags.split(",")

    whitelisted_tags = os.getenv("VERSION_SWITCHER_TAG_WHITELIST", default=[])
    whitelisted_tags = whitelisted_tags.split(",")

    # Retrieve and filter git tags
    repo = git.Repo("./")
    tags = [str(x) for x in repo.tags]
    tags = latest_tags_filter(tags, start_version)

    # Removing blacklisted tags and adding whitelisted tags.
    tags = [x for x in tags if x not in blacklisted_tags]
    tags = tags + [x for x in whitelisted_tags if x not in tags]

    # Sort the tags for the version switcher button.
    tags.sort(key=lambda x: x.replace("v", "").split("."))
    tags.reverse()

    # Create the version switcher
    switcher_json = []

    latest_data = {
        "name": "latest",
        "version": "master",
        "url": "https://deeppavlov.github.io/chatsky/master/",
    }
    switcher_json += [latest_data]

    dev_data = {
        "version": "dev",
        "url": "https://deeppavlov.github.io/chatsky/dev/",
    }
    switcher_json += [dev_data]

    for tag in tags:
        url = "https://deeppavlov.github.io/chatsky/" + str(tag) + "/"
        tag_data = {
            "name": str(tag),
            "version": str(tag),
            "url": url,
        }
        switcher_json += [tag_data]

    switcher_json_obj = json.dumps(switcher_json, indent=4)

    # Write nested JSON data to the switcher.json file
    with open("./docs/source/_static/switcher.json", "w") as f:
        f.write(switcher_json_obj)
