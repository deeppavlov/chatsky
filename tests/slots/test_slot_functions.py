from typing import Union, Any
import logging

import pytest

from chatsky import Context
from chatsky.core import BaseResponse, Node
from chatsky.core.message import MessageInitTypes, Message
from chatsky.slots.slots import ValueSlot, SlotNotExtracted, GroupSlot, SlotManager
from chatsky import conditions as cnd, responses as rsp, processing as proc
from chatsky.processing.slots import logger as proc_logger
from chatsky.slots.slots import logger as slot_logger
from chatsky.responses.slots import logger as rsp_logger


class MsgLen(ValueSlot):
    offset: int = 0
    exception: bool = False

    def extract_value(self, ctx: Context) -> Union[Any, SlotNotExtracted]:
        if self.exception:
            raise RuntimeError()
        return len(ctx.last_request.text) + self.offset


@pytest.fixture
def root_slot():
    return GroupSlot.model_validate({"0": MsgLen(offset=0), "1": MsgLen(offset=1), "err": MsgLen(exception=True)})


@pytest.fixture
def context(root_slot):
    ctx = Context()
    ctx.add_request("text")
    ctx.framework_data.slot_manager = SlotManager()
    ctx.framework_data.slot_manager.set_root_slot(root_slot)
    return ctx


@pytest.fixture
def manager(context):
    return context.framework_data.slot_manager


@pytest.fixture
def call_logger_factory():
    def inner():
        logs = []
        def func(*args, **kwargs):
            logs.append({"args": args, "kwargs": kwargs})

        return logs, func
    return inner


async def test_basic_functions(context, manager, log_event_catcher):
    proc_logs = log_event_catcher(proc_logger, level=logging.ERROR)
    slot_logs = log_event_catcher(slot_logger, level=logging.ERROR)

    await proc.Extract("0", "2", "err").wrapped_call(context)

    assert manager.get_extracted_slot("0").value == 4
    assert manager.is_slot_extracted("1") is False
    assert isinstance(manager.get_extracted_slot("err").extracted_value, RuntimeError)

    assert len(proc_logs) == 1
    assert len(slot_logs) == 1

    assert await cnd.SlotsExtracted("0", "1", mode="any").wrapped_call(context) is True
    assert await cnd.SlotsExtracted("0", "1", mode="all").wrapped_call(context) is False
    assert await cnd.SlotsExtracted("0", mode="all").wrapped_call(context) is True

    await proc.Unset("2", "0", "1").wrapped_call(context)
    assert manager.is_slot_extracted("0") is False
    assert manager.is_slot_extracted("1") is False
    assert isinstance(manager.get_extracted_slot("err").extracted_value, RuntimeError)

    assert len(proc_logs) == 2

    assert await cnd.SlotsExtracted("0", "1", mode="any").wrapped_call(context) is False


async def test_extract_all(context, manager, monkeypatch, call_logger_factory):
    logs, func = call_logger_factory()

    monkeypatch.setattr(SlotManager, "extract_all", func)

    await proc.ExtractAll().wrapped_call(context)

    assert logs == [{"args": (manager, context), "kwargs": {}}]


async def test_unset_all(context, manager, monkeypatch, call_logger_factory):
    logs, func = call_logger_factory()

    monkeypatch.setattr(SlotManager, "unset_all_slots", func)

    await proc.UnsetAll().wrapped_call(context)

    assert logs == [{"args": (manager,), "kwargs": {}}]


class TestTemplateFilling:
    async def test_failed_template(self, context, call_logger_factory):
        class MyResponse(BaseResponse):
            async def call(self, ctx: Context) -> MessageInitTypes:
                raise RuntimeError()

        with pytest.raises(ValueError):
            await rsp.FilledTemplate(MyResponse()).call(context)

    async def test_missing_text(self, context, log_event_catcher):
        logs = log_event_catcher(rsp_logger, level=logging.WARN)

        assert await rsp.FilledTemplate({}).wrapped_call(context) == Message()
        assert len(logs) == 1

    async def test_normal_execution(self, context, manager):
        await manager.extract_all(context)

        template_message = Message(text="{0} {1}")
        assert await rsp.FilledTemplate(template_message).wrapped_call(context) == Message("4 5")
        assert template_message.text == "{0} {1}"

    @pytest.mark.parametrize("on_exception,result", [
        ("return_none", Message()),
        ("keep_template", Message("{0} {1} {2}"))
    ])
    async def test_on_exception(self, context, manager, on_exception, result):
        await manager.extract_all(context)

        assert await rsp.FilledTemplate("{0} {1} {2}", on_exception=on_exception).wrapped_call(context) == result

    async def test_fill_template_proc_empty(self, context):
        context.framework_data.current_node = Node()

        await proc.FillTemplate().wrapped_call(context)

        assert context.current_node.response is None

    async def test_fill_template_proc(self, context):
        context.framework_data.current_node = Node(response="text")

        await proc.FillTemplate().wrapped_call(context)

        assert context.current_node.response == rsp.FilledTemplate(template=Message("text"))
