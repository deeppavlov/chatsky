import importlib
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing import check_happy_path, HAPPY_PATH

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "tutorial_module_name",
    [
        "1_basics",
        "2_pre_and_post_processors",
        "3_pipeline_dict_with_services_basic",
        "3_pipeline_dict_with_services_full",
        "4_groups_and_conditions_basic",
        "4_groups_and_conditions_full",
        "5_asynchronous_groups_and_services_basic",
        "5_asynchronous_groups_and_services_full",
        "6_extra_handlers_basic",
        "6_extra_handlers_full",
        "7_extra_handlers_and_extensions",
    ],
)
def test_tutorials(tutorial_module_name: str):
    try:
        tutorial_module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    except ModuleNotFoundError as e:
        pytest.skip(f"dependencies unavailable: {e.msg}")
    check_happy_path(tutorial_module.pipeline, HAPPY_PATH)
