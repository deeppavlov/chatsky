import importlib

from tests.test_utils import get_path_from_tests_to_current_dir


dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


def test_pretty_format():
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.5_asynchronous_groups_and_services_full")
    example_module.pipeline.pretty_format()
