"""
This script ensures that example scripts can successfully compile and are ready to run
"""
import os
import asyncio
import datetime
from multiprocessing import Process
import importlib

import pytest

from dff.utils.testing.toy_script import HAPPY_PATH
from dff.utils.testing.common import check_happy_path
from tests.test_utils import get_path_from_tests_to_current_dir

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


def test_unhappy_path(pipeline_instance):
    with pytest.raises(Exception) as e:
        check_happy_path(pipeline_instance, (("Hi", "false_response"),))
    assert e


@pytest.mark.parametrize(
    "example_module_name",
    [
        "1_basic",
        "9_polling_setup",
        "10_webhook_setup"
    ],
)
def test_examples(example_module_name):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    check_happy_path(example_module.pipeline, HAPPY_PATH)


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="`TG_BOT_TOKEN` missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
@pytest.mark.asyncio
@pytest.mark.parametrize("example_module_name", [
    "6_conditions",
])
async def test_client_examples(example_module_name, bot_id, tg_client):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    pipeline = example_module.pipeline
    process = Process(target=pipeline.run, args=(), daemon=True)
    process.start()
    happy_path = example_module.happy_path
    await asyncio.sleep(6)
    for request, response in happy_path:
        await tg_client.send_message(bot_id, request)
        sending_time = datetime.datetime.now() - datetime.timedelta(seconds=5)
        await asyncio.sleep(3)
        messages = await tg_client.get_messages(bot_id, limit=5, offset_date=sending_time)
        print(*[f"{i.id} {'user' if i.out else 'bot'}: {i.text}" for i in messages], sep="\n")
        assert messages[0].out is False
        assert messages[0].text == response
    process.kill()
