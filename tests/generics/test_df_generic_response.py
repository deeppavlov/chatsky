import pytest
from pydantic import BaseModel

from .examples.example_utils import run_test
from .examples import basics
from .examples import buttons


@pytest.mark.parametrize(["module"], [(basics, ), (buttons, )])
def test_examples(module):
    actor = getattr(module, "actor")
    testing_dialog = getattr(module, "testing_dialog")
    run_test(testing_dialog=testing_dialog, actor=actor)
