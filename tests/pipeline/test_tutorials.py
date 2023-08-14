import importlib
import pytest

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing import check_happy_path, HAPPY_PATH
from dff.script import Message

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


def test_custom_messenger_interface_tutorial():
    tutorial_module_name = "6_custom_messenger_interface"
    try:
        tutorial_module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    except ModuleNotFoundError as e:
        pytest.skip(f"dependencies unavailable: {e.msg}")

    happy_path = tuple(
        (req, Message(misc={"webpage": tutorial_module.construct_webpage_by_response(res.text)}))
        for req, res in HAPPY_PATH
    )
    check_happy_path(tutorial_module.pipeline, happy_path)
