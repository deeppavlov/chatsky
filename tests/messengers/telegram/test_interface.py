import pytest
import inspect
import time
import os

from telebot import types
from dff.script import Context
from dff.messengers.telegram import PollingTelegramInterface
from dff.messengers.telegram import extract_telegram_request_and_id

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")


def create_text_message(text: str):
    params = {"text": text}
    chat = types.User("1", False, "test")
    return types.Message(1, chat, None, chat, "text", params, "")


def create_query(data: str):
    chat = types.User("1", False, "test")
    return types.CallbackQuery(1, chat, data, chat)


def create_update(**kwargs):
    none_dict = {key: None for key in list(inspect.signature(types.Update).parameters.keys())}
    return types.Update(**{**none_dict, **kwargs})


@pytest.mark.parametrize(
    [
        "update",
    ],
    [(create_text_message("hello"),), (create_text_message("hi"),)],
)
def test_set_update(update):
    ctx = Context()
    ctx.add_request(update)
    assert ctx.last_request


@pytest.mark.skipif(TG_BOT_TOKEN is None, reason="`TG_BOT_TOKEN` is missing.")
@pytest.mark.parametrize(
    [
        "update",
    ],
    [
        (create_update(update_id=1, message=create_text_message("hello")),),
        (create_update(update_id=1, message=create_text_message("hi")),),
    ],
)
@pytest.mark.asyncio
async def test_update_handling(pipeline_instance, update, basic_bot, user_id):
    interface = PollingTelegramInterface(messenger=basic_bot)
    inner_update, _id = extract_telegram_request_and_id(interface.messenger, update)
    assert isinstance(inner_update, types.JsonDeserializable)
    assert _id == "1"
    interface.messenger.remove_webhook()
    counter = 0
    while counter != 4:
        counter += 1
        try:
            await interface.connect(pipeline_instance._run_pipeline, loop=lambda: None)
            except_result = interface._on_exception(Exception())
            assert except_result is None
            request_result = interface._request()
            assert isinstance(request_result, list)
            response_result = interface._respond([Context(id=user_id, responses={0: "hi"})])
            assert response_result is None
            break
        except Exception:
            time.sleep(2)


@pytest.mark.skipif(TG_BOT_TOKEN is None, reason="`TG_BOT_TOKEN` is missing.")
@pytest.mark.parametrize(
    "message,expected", [(create_text_message("Hello"), True), (create_text_message("Goodbye"), False)]
)
def test_message_handling(message, expected, actor_instance, basic_bot):
    condition = basic_bot.cnd.message_handler(func=lambda msg: msg.text == "Hello")
    context = Context(id=123)
    context.add_request(message)
    assert condition(context, actor_instance) == expected
    wrong_type = create_query("some data")
    context.add_request(wrong_type)
    assert not condition(context, actor_instance)


@pytest.mark.skipif(TG_BOT_TOKEN is None, reason="`TG_BOT_TOKEN` is missing.")
@pytest.mark.parametrize("query,expected", [(create_query("4"), True), (create_query("5"), False)])
def test_query_handling(query, expected, actor_instance, basic_bot):
    condition = basic_bot.cnd.callback_query_handler(func=lambda call: call.data == "4")
    context = Context(id=123)
    context.add_request(query)
    assert condition(context, actor_instance) == expected
    wrong_type = create_text_message("some text")
    context.add_request(wrong_type)
    assert not condition(context, actor_instance)
