from docs.source.utils.notebook import py_percent_to_notebook  # noqa: E402
from docs.source.utils.generate_tutorials import generate_tutorial_links_for_notebook_creation  # noqa: E402
from docs.source.utils.link_misc_files import link_misc_files  # noqa: E402
from docs.source.utils.regenerate_apiref import regenerate_apiref  # noqa: E402
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
            ("tutorials.utils", "Utils"),
            ("tutorials.stats", "Stats"),
        ],
        source=(root_dir + "/tutorials"),
        destination=(root_dir + "/docs/source/tutorials"),
    )
    regenerate_apiref(
        [
            ("dff.context_storages", "Context Storages"),
            ("dff.messengers", "Messenger Interfaces"),
            ("dff.pipeline", "Pipeline"),
            ("dff.script", "Script"),
            ("dff.stats", "Stats"),
            ("dff.utils.testing", "Testing Utils"),
            ("dff.utils.turn_caching", "Caching"),
            ("dff.utils.db_benchmark", "DB Benchmark"),
        ],
        root_dir=root_dir,
    )

