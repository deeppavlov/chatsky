from typing import List, Tuple
import importlib

import pytest
from dff.core.engine.core import Context
from dff.core.pipeline import Pipeline
import tests.utils as utils

dot_path_to_addon = utils.get_dot_path_from_tests_to_current_dir(__file__)

TURNS = [
    ("hi", "how are you"),
    ("fine", "what would you like to talk about?"),
    ("dog", "do you like it?"),
    ("yes", "what animals do you have?"),
]


def run_pipeline_test(pipeline: Pipeline, turns: List[Tuple[str, str]]):
    ctx = Context()
    for turn_id, (request, true_response) in enumerate(turns):
        ctx = pipeline(request, ctx.id)
        if true_response != ctx.last_response:
            msg = f" pipeline={pipeline}"
            msg += f" turn_id={turn_id}"
            msg += f" request={request} "
            msg += f"\ntrue_response != out_response: "
            msg += f"\n{true_response} != {ctx.last_response}"
            raise Exception(msg)


@pytest.mark.parametrize(
    "example_module_name",
    [
        "1_services_basic",
        "2_services_advanced",
        "3_service_groups_basic",
        "4_service_groups_advanced",
        "5_global_services_basic",
        "6_global_services_advanced",
    ],
)
def test_examples(example_module_name: str, testing_file: str):
    module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    try:
        pipeline = module.pipeline
        stats = module.StatsStorage.from_uri(f"csv://{testing_file}", "")
        stats.add_extractor_pool(module.extractor_pool)
        run_pipeline_test(pipeline, TURNS)
        with open(testing_file, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()
            assert len(lines) > 1
    except Exception as exc:
        raise Exception(f"model_name=examples.{dot_path_to_addon}.{example_module_name}") from exc
