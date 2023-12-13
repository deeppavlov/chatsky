# flake8: noqa
import os
import json
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


def post_comment_on_pr(comment: str, pr_number: int):
    """
    Leave a comment as `github-actions` bot on a PR.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f'Bearer {GITHUB_ARGS["GITHUB_TOKEN"]}',
        "X-GitHub-Api-Version": "2022-11-28",
    }

    escaped_comment = comment.replace("\n", "\\n")

    data = f'{{"body": "{escaped_comment}","event": "COMMENT","comments": []}}'

    response = requests.post(
        f'https://api.github.com/repos/{GITHUB_ARGS["GITHUB_REPOSITORY"]}/pulls/{pr_number}/reviews',
        headers=headers,
        data=data,
    )

    if not response.status_code == 200:
        raise RuntimeError(response.__dict__)


RELEASE_CHECKLIST = """It appears this PR is a release PR (change its base from `master` if that is not the case).

Here's a release checklist:

- [ ] Update package version
- [ ] Change PR merge option
- [ ] Test modules without automated testing:
  - [ ] Requiring telegram `api_id` and `api_hash`
  - [ ] Requiring `HF_API_KEY`
- [ ] Search for objects to be deprecated
"""


def post_release_checklist(pr_payload: dict):
    pr_number = pr_payload["number"]
    pr_base = pr_payload["base"]

    if pr_base["ref"] == "master":
        print("post_release_checklist")
        post_comment_on_pr(RELEASE_CHECKLIST, pr_number)


def on_opened_pull_request(event_info: dict):
    print("on_opened_pull_request")

    post_release_checklist(event_info["pull_request"])


def main():
    with open(GITHUB_ARGS["GITHUB_EVENT_PATH"], "r", encoding="utf-8") as fd:
        event_info = json.load(fd)
    print(f"event info: {event_info}")
    if GITHUB_ARGS["GITHUB_EVENT_NAME"] == "pull_request_target" and event_info["action"] == "opened":
        on_opened_pull_request(event_info)


if __name__ == "__main__":
    main()
