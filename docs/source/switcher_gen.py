import git
import json

def generate_switcher():
    repo = git.Repo('./')
    branch = repo.active_branch
    
    tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
    tags.reverse()
    latest_tag = tags[-1]
    
    switcher_json = []
    
    dev_data = {
        "version": "dev",
        "url": "https://zerglev.github.io/dialog_flow_framework/dev/index.html",
    }
    switcher_json += [dev_data]
    
    master_data = {
        "name": "master",
        "version": "v0.7.0",
        "url": "https://zerglev.github.io/dialog_flow_framework/master/index.html",
        "preferred": "true",
    }
    switcher_json += [master_data]
    
    for tag in tags:
        url = "https://zerglev.github.io/dialog_flow_framework/" + str(tag) + "/index.html"
        tag_data = {
            "name": str(tag),
            "version": str(tag),
            "url": url,
        }
        if tag == tags[0]:
            tag_data["preferred"] = "true"
        # Only building for tags from v0.7.0
        if str(tag) > "v0.7.0":
            switcher_json += [tag_data]
    
    switcher_json_obj = json.dumps(switcher_json, indent=4)
    
    # Write nested JSON data to the switcher.json file
    with open('./docs/source/_static/switcher.json', 'w') as f:
        f.write(switcher_json_obj)

