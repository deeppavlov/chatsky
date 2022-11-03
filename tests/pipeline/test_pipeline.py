import importlib
import os
import sys

import tests.utils as utils


# TODO: remove this as soon as utils will be moved to PYPI
sys.path.append(os.path.abspath(f"examples/{utils.get_path_from_tests_to_current_dir(__file__)}"))

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")

sys.path.append(str((pathlib.Path(__file__).parent / 'examples').absolute()))

def test_pretty_format():
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.5_asynchronous_groups_and_services_full")
    example_module.pipeline.pretty_format()
