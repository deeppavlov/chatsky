import sys
import os
from pathlib import Path
import importlib

import pytest

import tests.utils as utils


# TODO: remove this as soon as utils will be moved to PYPI
sys.path.append(os.path.abspath(f"examples/{utils.get_path_from_tests_to_current_dir(__file__)}"))

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")

from _extended_conditions_utils import run_test


@pytest.mark.parametrize(
    ["module_name"],
    [
        ("base_example",),
        ("remote_api.rasa",),
        ("remote_api.dialogflow",),
        ("remote_api.hf_api",),
        ("gensim_example",),
        ("sklearn_example",),
    ],
)
def test_examples(module_name):
    module = importlib.import_module(module_name)
    actor = getattr(module, "actor")
    testing_dialog = getattr(module, "testing_dialogue")
    run_test(testing_dialog=testing_dialog, actor=actor)
