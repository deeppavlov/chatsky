import importlib

from tests.test_utils import get_path_from_tests_to_current_dir


dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


def test_pretty_format():
    tutorial_module = importlib.import_module(f"tutorials.{dot_path_to_addon}.5_asynchronous_groups_and_services_full")
    tutorial_module.pipeline.pretty_format()
