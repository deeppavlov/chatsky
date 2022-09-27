import os
import sys
import importlib
import pathlib

import pytest

from examples._utils import auto_run_pipeline


# Uncomment the following line, if you want to run your examples during the test suite or import from them
# pytest.skip(allow_module_level=True)


@pytest.mark.parametrize(
    "module_name", [file.stem for file in pathlib.Path("examples").glob("*.py") if not file.stem.startswith("_")]
)
def test_examples(module_name: str):
    sys.path.append(os.path.abspath("./examples"))
    module = importlib.import_module(f"examples.{module_name}")
    if module_name.startswith("6"):
        auto_run_pipeline(module.pipeline, wrapper=module.construct_webpage_by_response)
    else:
        auto_run_pipeline(module.pipeline)
