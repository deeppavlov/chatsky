"""
This script ensures that example scripts can successfully compile and are ready to run
"""
import os
import datetime
import importlib
import time
import pytz
from multiprocessing import Process

import pytest
from tests.test_utils import get_path_from_tests_to_current_dir

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")
UTC = pytz.UTC

dot_path_to_addon = get_path_from_tests_to_current_dir(__file__, separator=".")


@pytest.mark.skipif(not TG_BOT_TOKEN, reason="TG_BOT_TOKEN missing")
@pytest.mark.skipif(not TG_API_ID or not TG_API_HASH, reason="TG credentials missing")
@pytest.mark.asyncio
@pytest.mark.parametrize("example_module_name", [
    "4_conditions",
    "7_polling_setup",
])
async def test_client_examples(example_module_name, bot_id, tg_client):
    example_module = importlib.import_module(f"examples.{dot_path_to_addon}.{example_module_name}")
    pipeline = example_module.pipeline
    process = Process(target=pipeline.run, args=(), daemon=True)
    process.start()
    happy_path = example_module.happy_path
    time.sleep(12)
    for request, response in happy_path:
        sending_time = datetime.datetime.now(tz=UTC) - datetime.timedelta(seconds=2)
        await tg_client.send_message(bot_id, request.text)
        time.sleep(2.5)
        messages = await tg_client.get_messages(bot_id, limit=5)
        new_messages = list(filter(lambda msg: msg.date >= sending_time, messages))
        print(*[f"{'bot' if not i.out else 'user'}: {i.text}: {i.date}" for i in new_messages], sep="\n")
        assert new_messages[0].out is False
        assert new_messages[0].text == response.text
    process.kill()
    while process.is_alive():
        time.sleep(0.1)
