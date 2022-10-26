import importlib

import tests.utils as utils


dot_path_to_addon = utils.get_dot_path_to_example_directory(__file__)


def test_pretty_format():
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.5_asynchronous_groups_and_services_full")
    example_module.pipeline.pretty_format()

