import sys
import os
from pathlib import Path
import importlib

import pytest

import tests.utils as utils

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")

from dff.utils.testing.common import check_happy_path


@pytest.mark.parametrize(
    ["example_module_name", "skip_condition"],
    [
        ("base_example", None),
        ("remote_api.rasa", os.getenv("RASA_API_KEY") is None),
        ("remote_api.dialogflow", not (os.getenv("GDF_ACCOUNT_JSON") and os.path.exists(os.getenv("GDF_ACCOUNT_JSON")))),
        ("remote_api.hf_api", os.getenv("HF_API_KEY") is None),
        ("gensim_example", None),
        ("sklearn_example", None),
    ],
)
def test_examples(example_module_name: str, skip_condition):
    module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    pipeline = getattr(module, "pipeline")
    happy_path = getattr(module, "happy_path")
    if skip_condition is not None:
        pytest.skip()
    check_happy_path(pipeline, happy_path)
