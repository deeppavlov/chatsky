import importlib

import pytest

import tests.utils as utils

dot_path_to_addon = utils.get_dot_path_from_tests_to_current_dir(__file__)
pipeline_utils = importlib.import_module(f"examples.{dot_path_to_addon}._pipeline_utils")


@pytest.mark.parametrize(
    "example_module_name",
    [
        "1_basic_example",
        "2_pre_and_post_processors",
        "3_pipeline_dict_with_services_basic",
        "3_pipeline_dict_with_services_full",
        "4_groups_and_conditions_basic",
        "4_groups_and_conditions_full",
        "5_asynchronous_groups_and_services_basic",
        "5_asynchronous_groups_and_services_full",
        "6_custom_messenger_interface",
        "7_extra_handlers_basic",
        "7_extra_handlers_full",
        "8_extra_handlers_and_extensions",
    ],
)
def test_examples(example_module_name: str):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    if example_module_name.startswith("6"):
        pipeline_utils.auto_run_pipeline(example_module.pipeline, wrapper=example_module.construct_webpage_by_response)
    else:
        pipeline_utils.auto_run_pipeline(example_module.pipeline)
