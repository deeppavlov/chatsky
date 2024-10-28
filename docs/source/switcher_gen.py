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
    # retrieving and sorting git tags
    repo = git.Repo('./')

    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    tags = [str(x) for x in tags]
    tags = latest_tags_filter(tags)

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
