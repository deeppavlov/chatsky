# flake8: noqa
import os
import json
import re
import requests

GITHUB_ARGS = {
    "GITHUB_TOKEN": None,
    "GITHUB_REPOSITORY": None,
    "GITHUB_EVENT_PATH": None,
    "GITHUB_EVENT_NAME": None,
}

for arg in GITHUB_ARGS:
    GITHUB_ARGS[arg] = os.getenv(arg)

    if GITHUB_ARGS[arg] is None:
        raise RuntimeError(f"`{arg}` is not set")
    else:
        print(arg, GITHUB_ARGS[arg])


def on_opened_pull_request(event_info: dict):
    print("Opened pr")
    with open(".github/PULL_REQUEST_TEMPLATE.md", "r", encoding="utf-8") as fd:
        contents = fd.read()
    template_body = re.escape(contents).replace("\-\ \[\ \]", "\-\ \[[ x]\]").replace("\\\n", "(\n|\r|\r\n)")
    template_body_pattern = re.compile(template_body)
    # this matches any string that equals PULL_REQUEST_TEMPLATE with checklist items checked or unchecked
    # (i.e. if instead of `- [ ]` string has `- [x]` it also counts)

    pr_number = event_info["pull_request"]["number"]
    pr_body = event_info["pull_request"]["body"]

    if pr_body is None or pr_body == "" or template_body_pattern.match(pr_body) is not None:
        print("Match found")
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f'Bearer {GITHUB_ARGS["GITHUB_TOKEN"]}',
            "X-GitHub-Api-Version": "2022-11-28",
        }

        data = '{"body": "Please provide a description: what is changed and why.","event": "COMMENT","comments": []}'

        response = requests.post(
            f'https://api.github.com/repos/{GITHUB_ARGS["GITHUB_REPOSITORY"]}/pulls/{pr_number}/reviews',
            headers=headers,
            data=data,
        )

        if not response.status_code == 200:
            raise RuntimeError(response.__dict__)


def main():
    with open(GITHUB_ARGS["GITHUB_EVENT_PATH"], "r", encoding="utf-8") as fd:
        event_info = json.load(fd)
    print(f"event info: {event_info}")
    if GITHUB_ARGS["GITHUB_EVENT_NAME"] == "pull_request_target" and event_info["action"] == "opened":
        on_opened_pull_request(event_info)


if __name__ == "__main__":
    main()
