from os import environ
from pathlib import Path
from string import Template
from typing import List, Dict, Tuple

from requests import post
from sphinx.util import logging

logger = logging.getLogger(__name__)

release_notes_query = """
query { 
  repository(owner: "deeppavlov", name: "dialog_flow_framework") {
    releases($pagination) {
      nodes {
        name
        descriptionHTML
      }
      pageInfo {
        endCursor
        hasNextPage
      }
    }
  }
}
"""


def run_github_api_releases_query(pagination, retries_count: int = 5) -> Tuple[List[Dict[str, str]], Dict[str, str]]:
    headers = {"Authorization": f"Bearer {environ['GTIHUB_API_TOKEN']}"}
    res = post("https://api.github.com/graphql", json={"query": Template(release_notes_query).substitute(pagination=pagination)}, headers=headers)
    if res.status_code == 200:
        response = res.json()
        return response["data"]["repository"]["releases"]["nodes"], response["data"]["repository"]["releases"]["pageInfo"]
    elif res.status_code == 502 and retries_count > 0:
        return run_github_api_releases_query(pagination, retries_count - 1)
    else:
        raise Exception(f"Query to GitHub API failed to run by returning code of {res.status_code}: {res.json()}")


def get_github_releases_paginated() -> List[Tuple[str, str]]:
    page_list, page_info = run_github_api_releases_query("first: 100")
    while page_info["hasNextPage"]:
        pagination = f'first: 100, after: "{page_info["endCursor"]}"'
        new_page_list, page_info = run_github_api_releases_query(pagination)
        page_list += new_page_list
    return [(node["name"], node["descriptionHTML"]) for node in page_list]


def pull_release_notes_from_github(path: str = "docs/source/release_notes.rst"):
    if "GTIHUB_API_TOKEN" not in environ:
        logger.warning("GitHub API token not defined ('GTIHUB_API_TOKEN' environmental variable not set)!")
    with open(Path(path), "w") as file:
        for name, desc in get_github_releases_paginated():
            description = "\n   ".join(desc.split("\n"))
            file.write(f"{name}\n{'-' * len(name)}\n\n.. raw:: html\n\n   {description}\n\n\n")
