from utils.generate_tutorials import generate_tutorial_links_for_notebook_creation  # noqa: E402
from utils.link_misc_files import link_misc_files  # noqa: E402
from utils.regenerate_apiref import regenerate_apiref  # noqa: E402


def setup():
    link_misc_files(
        [
            "utils/db_benchmark/benchmark_schema.json",
            "utils/db_benchmark/benchmark_streamlit.py",
        ]
    )
    generate_tutorial_links_for_notebook_creation(
        [
            ("tutorials.context_storages", "Context Storages"),
            (
                "tutorials.messengers",
                "Interfaces",
                [
                    ("telegram", "Telegram"),
                    ("web_api_interface", "Web API"),
                ],
            ),
            ("tutorials.service", "Service"),
            (
                "tutorials.script",
                "Script",
                [
                    ("core", "Core"),
                    ("responses", "Responses"),
                ],
            ),
            ("tutorials.llm", "LLM Integration"),
            ("tutorials.slots", "Slots"),
            ("tutorials.stats", "Stats"),
        ]
    )
    regenerate_apiref(
        [
            ("chatsky.core.service", "Core.Service"),
            ("chatsky.core", "Core"),
            ("chatsky.conditions", "Conditions"),
            ("chatsky.destinations", "Destinations"),
            ("chatsky.responses", "Responses"),
            ("chatsky.processing", "Processing"),
            ("chatsky.context_storages", "Context Storages"),
            ("chatsky.messengers", "Messenger Interfaces"),
            ("chatsky.llm", "LLM Integration"),
            ("chatsky.slots", "Slots"),
            ("chatsky.stats", "Stats"),
            ("chatsky.utils.testing", "Testing Utils"),
            ("chatsky.utils.db_benchmark", "DB Benchmark"),
            ("chatsky.utils.devel", "Development Utils"),
        ]
    )
