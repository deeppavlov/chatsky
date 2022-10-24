import sys
import importlib
import pathlib

import pytest
from pydantic import BaseModel


from .examples.example_utils import run_test


@pytest.mark.parametrize("module_name", ["examples.basics", "examples.buttons", "examples.media"])
def test_examples(module_name):
    module = importlib.import_module(f"tests.generics.{module_name}")
    actor = getattr(module, "actor")
    testing_dialog = getattr(module, "testing_dialog")
    run_test(testing_dialog=testing_dialog, actor=actor)
