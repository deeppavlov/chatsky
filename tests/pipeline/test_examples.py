import importlib
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing import check_happy_path, HAPPY_PATH
from dff.script import Message

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "example_module_name",
    [
        "1_basics",
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
        happy_path = tuple(
            (req, Message(misc={"webpage": example_module.construct_webpage_by_response(res.text)}))
            for req, res in HAPPY_PATH
        )
        check_happy_path(example_module.pipeline, happy_path)
    else:
        check_happy_path(example_module.pipeline, HAPPY_PATH)
