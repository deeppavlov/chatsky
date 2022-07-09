import sys
import importlib

import pytest

import df_slots

# uncomment the following line, if you want to run your examples during the test suite or import from them
sys.path.insert(0, "../")

from examples.example_utils import run_test

# pytest.skip(allow_module_level=True)


@pytest.mark.parametrize(
    "module_name",
    [
        "examples.generics_example",
        # "examples.basic_example",
        "examples.handlers_example",
        "examples.form_example",
    ],
)
def test_examples(module_name, root):
    root.children.clear()
    # print(df_slots.root_slot.children)
    module = importlib.import_module(module_name)
    actor = getattr(module, "actor")
    testing_dialog = getattr(module, "testing_dialog")
    if hasattr(module, "stmt"):
        print(getattr(module, "stmt"))
    run_test(testing_dialog=testing_dialog, actor=actor)
