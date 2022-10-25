import sys
import importlib
import pathlib

import pytest
from pydantic import BaseModel


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "examples"))

from .examples.example_utils import run_test
from .examples import media
from .examples import basics
from .examples import buttons


@pytest.mark.parametrize(["module"], [(basics, ), (buttons, ), (media, )])
def test_examples(module):
    actor = getattr(module, "actor")
    testing_dialog = getattr(module, "testing_dialog")
    run_test(testing_dialog=testing_dialog, actor=actor)
