import sys

import pytest

from telebot import types
from df_engine.core.context import Context


def create_text_message(text: str):
    params = {"text": text}
    chat = types.User("1", False, "test")
    return types.Message(1, chat, None, chat, "text", params, "")


def create_query(data: str):
    chat = types.User("1", False, "test")
    return types.CallbackQuery(1, chat, data, chat)


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
    assert condition(context, actor_instance) == False


@pytest.mark.parametrize("query,expected", [(create_query("4"), True), (create_query("5"), False)])
def test_query_handling(query, expected, actor_instance, basic_bot):
    condition = basic_bot.cnd.callback_query_handler(func=lambda call: call.data == "4")
    context = Context(id=123)
    context.framework_states["TELEGRAM_CONNECTOR"] = {"keep_flag": True, "data": query}
    assert condition(context, actor_instance) == expected
    wrong_type = create_text_message("some text")
    context.framework_states["TELEGRAM_CONNECTOR"]["data"] = wrong_type
    assert condition(context, actor_instance) == False
