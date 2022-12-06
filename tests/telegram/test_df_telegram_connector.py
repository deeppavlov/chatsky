import pytest
import inspect
import time

from telebot import types
from dff.core.engine.core.context import Context
from dff.connectors.messenger.telegram.interface import PollingTelegramInterface
from dff.connectors.messenger.telegram.utils import set_state, get_initial_context


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
    set_state(ctx, update)
    assert ctx.framework_states["TELEGRAM_CONNECTOR"]["data"]
    assert ctx.last_request


def test_initial():
    _id = 123
    ctx = get_initial_context(_id)
    assert "TELEGRAM_CONNECTOR" in ctx.framework_states
    assert ctx.id == _id


@pytest.mark.parametrize(
    [
        "param",
    ],
    [
        (create_update(update_id=1, message=create_text_message("hello")),),
        (create_update(update_id=1, message=create_text_message("hi")),),
    ],
)
@pytest.mark.asyncio
async def test_update_handling(pipeline_instance, param, basic_bot, user_id):
    interface = PollingTelegramInterface(bot=basic_bot)
    inner_update, _id = interface._extract_telegram_request_and_id(param)
    assert isinstance(inner_update, types.JsonDeserializable)
    assert _id == "1"
    interface.bot.remove_webhook()
    counter = 0
    while counter != 4:
        counter += 1
        try:
            await interface.connect(pipeline_instance._run_pipeline, loop=lambda: None)
            except_result = interface._except(Exception())
            assert except_result is None
            request_result = interface._request()
            assert isinstance(request_result, list)
            response_result = interface._respond([Context(id=user_id, responses={0: "hi"})])
            assert response_result is None
            break
        except Exception:
            time.sleep(2)


@pytest.mark.parametrize(
    "message,expected", [(create_text_message("Hello"), True), (create_text_message("Goodbye"), False)]
)
def test_message_handling(message, expected, actor_instance, basic_bot):
    condition = basic_bot.cnd.message_handler(func=lambda msg: msg.text == "Hello")
    context = Context(id=123)
    context.framework_states["TELEGRAM_CONNECTOR"] = {"keep_flag": True, "data": message}
    assert condition(context, actor_instance) == expected
    wrong_type = create_query("some data")
    context.framework_states["TELEGRAM_CONNECTOR"]["data"] = wrong_type
    assert not condition(context, actor_instance)


@pytest.mark.parametrize("query,expected", [(create_query("4"), True), (create_query("5"), False)])
def test_query_handling(query, expected, actor_instance, basic_bot):
    condition = basic_bot.cnd.callback_query_handler(func=lambda call: call.data == "4")
    context = Context(id=123)
    context.framework_states["TELEGRAM_CONNECTOR"] = {"keep_flag": True, "data": query}
    assert condition(context, actor_instance) == expected
    wrong_type = create_text_message("some text")
    context.framework_states["TELEGRAM_CONNECTOR"]["data"] = wrong_type
    assert not condition(context, actor_instance)
