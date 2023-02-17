"""
These tests check that pipelines defined in examples follow `happy_path` defined in the same examples.
"""
import importlib
import logging

import pytest
from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.common import check_happy_path
from dff.utils.testing.telegram import TelegramTesting, replace_click_button

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "example_module_name",
    [
        "1_basic",
        "2_buttons",
        "3_buttons_with_callback",
    ],
)
def test_client_examples_without_telegram(example_module_name):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    pipeline = example_module.pipeline
    happy_path = example_module.happy_path
    check_happy_path(pipeline, replace_click_button(happy_path))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "example_module_name",
    [
        "1_basic",
        "2_buttons",
        "3_buttons_with_callback",
        "4_conditions",
        "5_conditions_with_media",
        "7_polling_setup",
    ],
)
async def test_client_examples(example_module_name, api_credentials, bot_user, session_file):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    pipeline = example_module.pipeline
    happy_path = example_module.happy_path
    test_helper = TelegramTesting(
        pipeline=pipeline, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    logging.info("Test start")
    await test_helper.check_happy_path(happy_path)
