import sys
import importlib
import os

import pytest

import dff.script.logic.slots

from tests import utils

# uncomment the following line, if you want to run your examples during the test suite or import from them
sys.path.append(os.path.abspath(f"examples/{utils.get_path_from_tests_to_current_dir(__file__)}"))

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")

from _slots_example_utils import run_test

# pytest.skip(allow_module_level=True)


@pytest.mark.parametrize(
    "module_name",
    [
        "generics_example",
        # "basic_example",
        "handlers_example",
        "form_example",
    ],
)
def test_examples(module_name, root):
    root.children.clear()
    # print(dff.script.logic.slots.root_slot.children)
    module = importlib.import_module(module_name)
    actor = getattr(module, "actor")
    testing_dialog = getattr(module, "testing_dialog")
    if hasattr(module, "stmt"):
        print(getattr(module, "stmt"))
    run_test(testing_dialog=testing_dialog, actor=actor)
