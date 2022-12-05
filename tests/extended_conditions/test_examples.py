import sys
import os
from pathlib import Path
import importlib

import pytest

import tests.utils as utils

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")

from dff.utils.testing.common import check_happy_path


@pytest.mark.parametrize(
    ["example_module_name"],
    [
        ("base_example",),
        ("remote_api.rasa",),
        ("remote_api.dialogflow",),
        ("remote_api.hf_api",),
        ("gensim_example",),
        ("sklearn_example",),
    ],
)
def test_examples(example_module_name: str):
    module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    pipeline = getattr(module, "pipeline")
    happy_path = getattr(module, "happy_path")
    check_happy_path(pipeline, happy_path)
