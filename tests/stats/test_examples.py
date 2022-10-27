from typing import List, Tuple
import pathlib
import importlib

import pytest
from df_engine.core import Context
from df_runner import Pipeline

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
    "module_path",
    [
        file
        for file in pathlib.Path(__file__).absolute().parent.parent.joinpath("examples").glob("*.py")
        if not file.stem.startswith("_")
    ],
)
def test_examples(module_path: pathlib.Path, testing_file: str):
    module = importlib.import_module(f"examples.{module_path.stem}")
    try:
        pipeline = module.pipeline
        stats = module.StatsStorage.from_uri(f"csv://{testing_file}", "")
        stats.add_extractor_pool(module.extractor_pool)
        run_pipeline_test(pipeline, TURNS)
        with open(testing_file, "r", encoding="utf-8") as file:
            lines = file.read().splitlines()
            assert len(lines) > 1
    except Exception as exc:
        raise Exception(f"model_name={module_path.stem}") from exc
