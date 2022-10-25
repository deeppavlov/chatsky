import sys
import importlib
import pathlib

import pytest
from pydantic import BaseModel


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "examples"))

from generics.example_utils import run_test


@pytest.mark.parametrize("module_name", ["generics.basics", "generics.buttons", "generics.media"])
def test_examples(module_name):
    module = importlib.import_module(f"{module_name}")
    actor = getattr(module, "actor")
    testing_dialog = getattr(module, "testing_dialog")
    run_test(testing_dialog=testing_dialog, actor=actor)
