import importlib
import pytest

import tests.utils as utils
from dff.utils.testing.common import check_happy_path
from dff.utils.testing.response_comparers import ref_in_cand_diff
from dff.utils.testing.toy_script import HAPPY_PATH

dot_path_to_addon = utils.get_path_from_tests_to_current_dir(__file__, separator=".")


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
    if example_module_name == "6_custom_messenger_interface":
        check_happy_path(example_module.pipeline, HAPPY_PATH, ref_in_cand_diff)
    else:
        check_happy_path(example_module.pipeline, HAPPY_PATH)
