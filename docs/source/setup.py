from docs.source.utils.generate_tutorials import generate_tutorial_links_for_notebook_creation
from docs.source.utils.link_misc_files import link_misc_files
from docs.source.utils.regenerate_apiref import regenerate_apiref
from pathlib import Path


def setup(root_dir: str, output_dir: str):
    link_misc_files(
        [
            "utils/db_benchmark/benchmark_schema.json",
            "utils/db_benchmark/benchmark_streamlit.py",
        ],
        root_dir=Path(root_dir),
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
            ("tutorials.pipeline", "Pipeline"),
            (
                "tutorials.script",
                "Script",
                [
                    ("core", "Core"),
                    ("responses", "Responses"),
                ],
            ),
            ("tutorials.slots", "Slots"),
            ("tutorials.stats", "Stats"),
        ],
        source=(root_dir + "/tutorials"),
        destination=(root_dir + "/docs/source/tutorials"),
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
            ("chatsky.slots", "Slots"),
            ("chatsky.stats", "Stats"),
            ("chatsky.utils.testing", "Testing Utils"),
            ("chatsky.utils.db_benchmark", "DB Benchmark"),
            ("chatsky.utils.devel", "Development Utils"),
        ],
        root_dir=root_dir,
    )
