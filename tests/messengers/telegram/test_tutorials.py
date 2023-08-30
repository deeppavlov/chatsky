"""
These tests check that pipelines defined in tutorials follow `happy_path` defined in the same tutorials.
"""
import importlib
import logging

import pytest

try:
    import telebot  # noqa: F401
    import telethon  # noqa: F401
except ImportError:
    pytest.skip(reason="`telegram` is not available", allow_module_level=True)

from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.common import check_happy_path
from dff.utils.testing.telegram import TelegramTesting, replace_click_button

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.parametrize(
    "tutorial_module_name",
    [
        "1_basic",
        "2_buttons",
        "3_buttons_with_callback",
    ],
)
def test_client_tutorials_without_telegram(tutorial_module_name, env_vars):
    tutorial_module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    pipeline = tutorial_module.pipeline
    happy_path = tutorial_module.happy_path
    check_happy_path(pipeline, replace_click_button(happy_path))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tutorial_module_name",
    [
        "1_basic",
        "2_buttons",
        "3_buttons_with_callback",
        "4_conditions",
        "5_conditions_with_media",
        "7_polling_setup",
    ],
)
@pytest.mark.telegram
async def test_client_tutorials(tutorial_module_name, api_credentials, bot_user, session_file):
    tutorial_module = importlib.import_module(f"tutorials.{dot_path_to_addon}.{tutorial_module_name}")
    pipeline = tutorial_module.pipeline
    happy_path = tutorial_module.happy_path
    test_helper = TelegramTesting(
        pipeline=pipeline, api_credentials=api_credentials, session_file=session_file, bot=bot_user
    )
    logging.info("Test start")
    await test_helper.check_happy_path(happy_path)
