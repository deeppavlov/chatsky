"""
These tests check that pipelines defined in examples follow `happy_path` defined in the same examples.
"""
import os
import importlib
import logging

import pytest
from tests.test_utils import get_path_from_tests_to_current_dir
from dff.utils.testing.telegram import TelegramTesting

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="TG_BOT_TOKEN missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
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
async def test_client_examples(example_module_name, tmp_path, api_credentials, bot_user):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    pipeline = example_module.pipeline
    happy_path = example_module.happy_path
    test_helper = TelegramTesting(pipeline=pipeline, api_credentials=api_credentials, bot=bot_user)
    logging.info("Test start")
    await test_helper.check_happy_path(happy_path, tmp_path)
